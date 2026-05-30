#!/usr/bin/env python3
"""
Phase 3A — Reconstruct daily hold paths for backtest trades.

Reads backtest_trades.csv and data/{ticker}.csv price series.
Uses the same 5-day hold window as step4_backtest.py (no strategy changes).

Outputs:
  backtest_daily_paths.csv
  backtest_daily_paths_validation.txt
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

HOLD_DAYS = 5
DATA_DIR = Path("data")
TRADES_PATH = Path("backtest_trades.csv")
PATHS_OUT = Path("backtest_daily_paths.csv")
VALIDATION_OUT = Path("backtest_daily_paths_validation.txt")

# Tolerances for cross-checks against backtest_trades.csv
PRICE_RTOL = 1e-4
RETURN_RTOL = 1e-5


def load_price_series() -> dict[str, pd.Series]:
    """Load close prices keyed by ticker stem (same convention as step4)."""
    prices: dict[str, pd.Series] = {}
    if not DATA_DIR.exists():
        return prices

    for f in DATA_DIR.glob("*.csv"):
        try:
            p = pd.read_csv(f, index_col=0)
            p.index = pd.to_datetime(p.index)
            col = "Adj Close" if "Adj Close" in p.columns else "Close"
            if col in p.columns:
                prices[f.stem] = p[col].sort_index()
        except Exception:
            continue
    return prices


def reconstruct_hold_path(
    stock_prices: pd.Series,
    signal_date: pd.Timestamp,
) -> tuple[pd.DatetimeIndex, np.ndarray] | None:
    """
    Return (hold_dates, hold_closes) for days 0..HOLD_DAYS inclusive.

    Day 0 = first close strictly after signal_date (matches step4 entry).
    """
    future = stock_prices[stock_prices.index > signal_date]
    if len(future) < HOLD_DAYS + 1:
        return None

    hold = future.iloc[0 : HOLD_DAYS + 1]
    return hold.index, hold.values.astype(float)


def build_path_rows(
    trade_id: int,
    ticker: str,
    signal_date: pd.Timestamp,
    hold_dates: pd.DatetimeIndex,
    hold_closes: np.ndarray,
) -> list[dict]:
    entry_price = hold_closes[0]
    if entry_price <= 0:
        return []

    cum_ret = hold_closes / entry_price - 1.0
    running_max = np.maximum.accumulate(cum_ret)
    drawdown_from_peak = cum_ret - running_max

    rows = []
    for day_idx in range(HOLD_DAYS + 1):
        rows.append(
            {
                "TradeID": trade_id,
                "Ticker": ticker,
                "EntryDate": signal_date.strftime("%Y-%m-%d"),
                "DayIndex": day_idx,
                "CloseDate": hold_dates[day_idx].strftime("%Y-%m-%d"),
                "Close": hold_closes[day_idx],
                "CumReturnFromEntry": cum_ret[day_idx],
                "RunningMaxReturn": running_max[day_idx],
                "DrawdownFromPeak": drawdown_from_peak[day_idx],
            }
        )
    return rows


def write_validation_report(
    trades: pd.DataFrame,
    paths_df: pd.DataFrame,
    missing: list[dict],
    quality: dict,
) -> None:
    lines = [
        "Phase 3A — Daily Hold Paths Validation Report",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "=" * 65,
        "SUMMARY",
        "=" * 65,
        f"Trades in backtest_trades.csv     : {len(trades):,}",
        f"Paths reconstructed (unique IDs)  : {paths_df['TradeID'].nunique() if len(paths_df) else 0:,}",
        f"Missing paths                     : {len(missing):,}",
        f"Path rows exported (6 per trade)  : {len(paths_df):,}",
        f"Expected rows if complete         : {len(trades) - len(missing):,} trades × {HOLD_DAYS + 1} days",
        "",
    ]

    if missing:
        lines.extend(["=" * 65, "MISSING PATHS", "=" * 65, ""])
        reason_counts = pd.Series([m["reason"] for m in missing]).value_counts()
        for reason, count in reason_counts.items():
            lines.append(f"  {reason}: {count:,}")
        lines.append("")
        lines.append("First 25 missing trades:")
        for m in missing[:25]:
            lines.append(
                f"  TradeID={m['trade_id']} {m['ticker']} signal={m['signal_date']} — {m['reason']}"
            )
        if len(missing) > 25:
            lines.append(f"  ... and {len(missing) - 25} more")
        lines.append("")

    lines.extend(
        [
            "=" * 65,
            "DATA QUALITY CHECKS",
            "=" * 65,
            "",
        ]
    )

    for check, result in quality.items():
        lines.append(f"{check}")
        lines.append(f"  {result}")
        lines.append("")

    lines.extend(
        [
            "=" * 65,
            "OUTPUT FILES",
            "=" * 65,
            f"  {PATHS_OUT}",
            f"  {VALIDATION_OUT}",
            "",
        ]
    )

    VALIDATION_OUT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    print("=" * 65)
    print(" Phase 3A: Reconstruct daily hold paths")
    print("=" * 65)

    if not TRADES_PATH.exists():
        raise FileNotFoundError(f"Missing {TRADES_PATH}. Run step4_backtest.py first.")

    trades = pd.read_csv(TRADES_PATH)
    trades["Date"] = pd.to_datetime(trades["Date"])

    print(f"\n Loading trades: {len(trades):,} rows")
    print(" Loading price data...")
    prices = load_price_series()
    print(f" Tickers in data/: {len(prices):,}")

    all_rows: list[dict] = []
    missing: list[dict] = []

    for trade_id, (_, row) in enumerate(trades.iterrows(), start=1):
        ticker = row["Ticker"]
        signal_date = row["Date"]

        if ticker not in prices:
            missing.append(
                {
                    "trade_id": trade_id,
                    "ticker": ticker,
                    "signal_date": signal_date.strftime("%Y-%m-%d"),
                    "reason": "ticker_not_in_data_folder",
                }
            )
            continue

        result = reconstruct_hold_path(prices[ticker], signal_date)
        if result is None:
            missing.append(
                {
                    "trade_id": trade_id,
                    "ticker": ticker,
                    "signal_date": signal_date.strftime("%Y-%m-%d"),
                    "reason": f"insufficient_future_bars (need {HOLD_DAYS + 1})",
                }
            )
            continue

        hold_dates, hold_closes = result
        rows = build_path_rows(trade_id, ticker, signal_date, hold_dates, hold_closes)
        if not rows:
            missing.append(
                {
                    "trade_id": trade_id,
                    "ticker": ticker,
                    "signal_date": signal_date.strftime("%Y-%m-%d"),
                    "reason": "invalid_entry_price",
                }
            )
            continue

        all_rows.extend(rows)

    paths_df = pd.DataFrame(all_rows)

    # Wide day-close columns for convenience (one row per trade in summary merge)
    if len(paths_df) > 0:
        wide_close = paths_df.pivot_table(
            index=["TradeID", "Ticker", "EntryDate"],
            columns="DayIndex",
            values="Close",
            aggfunc="first",
        )
        wide_close.columns = [f"Day{d}_Close" for d in wide_close.columns]
        wide_close = wide_close.reset_index()

        paths_export = paths_df.merge(
            wide_close, on=["TradeID", "Ticker", "EntryDate"], how="left"
        )
        col_order = (
            ["TradeID", "Ticker", "EntryDate", "DayIndex", "CloseDate"]
            + [f"Day{d}_Close" for d in range(HOLD_DAYS + 1)]
            + ["Close", "CumReturnFromEntry", "RunningMaxReturn", "DrawdownFromPeak"]
        )
        paths_export = paths_export[[c for c in col_order if c in paths_export.columns]]
    else:
        paths_export = paths_df

    paths_export.to_csv(PATHS_OUT, index=False)
    print(f"\n Saved -> {PATHS_OUT} ({len(paths_export):,} rows)")

    # Quality checks vs backtest_trades.csv
    quality: dict[str, str] = {}

    if len(paths_df) == 0:
        quality["status"] = "FAIL — no paths reconstructed (is data/ populated?)"
    else:
        day0 = paths_df[paths_df["DayIndex"] == 0][
            ["TradeID", "Close", "CumReturnFromEntry"]
        ].rename(columns={"Close": "Day0_Close", "CumReturnFromEntry": "Day0_Cum"})
        day5 = paths_df[paths_df["DayIndex"] == HOLD_DAYS][
            ["TradeID", "Close", "CumReturnFromEntry"]
        ].rename(
            columns={
                "Close": "Day5_Close",
                "CumReturnFromEntry": "Day5_CumGross",
            }
        )

        check = trades.reset_index(drop=True).copy()
        check["TradeID"] = np.arange(1, len(check) + 1)
        check = check.merge(day0, on="TradeID", how="left").merge(day5, on="TradeID", how="left")

        reconstructed_ids = set(paths_df["TradeID"].unique())
        check_recon = check[check["TradeID"].isin(reconstructed_ids)]

        entry_match = np.isclose(
            check_recon["Day0_Close"],
            check_recon["EntryPrice"],
            rtol=PRICE_RTOL,
            atol=1e-3,
            equal_nan=False,
        )
        exit_match = np.isclose(
            check_recon["Day5_Close"],
            check_recon["ExitPrice"],
            rtol=PRICE_RTOL,
            atol=1e-3,
            equal_nan=False,
        )
        gross_match = np.isclose(
            check_recon["Day5_CumGross"],
            check_recon["GrossReturn"],
            rtol=RETURN_RTOL,
            atol=1e-6,
            equal_nan=False,
        )

        quality["entry_price_vs_day0_close"] = (
            f"{entry_match.sum():,} / {len(check_recon):,} match "
            f"({entry_match.mean() * 100:.2f}%)"
        )
        quality["exit_price_vs_day5_close"] = (
            f"{exit_match.sum():,} / {len(check_recon):,} match "
            f"({exit_match.mean() * 100:.2f}%)"
        )
        quality["gross_return_vs_day5_cumulative"] = (
            f"{gross_match.sum():,} / {len(check_recon):,} match "
            f"({gross_match.mean() * 100:.2f}%)"
        )

        # Path metric consistency (final day)
        final = paths_df[paths_df["DayIndex"] == HOLD_DAYS]
        mg_match = np.isclose(
            final["RunningMaxReturn"].values,
            check_recon.set_index("TradeID").loc[final["TradeID"], "MaxGainDuringHold"].values,
            rtol=RETURN_RTOL,
            atol=1e-6,
        )
        quality["running_max_day5_vs_MaxGainDuringHold"] = (
            f"{mg_match.sum():,} / {len(final):,} match ({mg_match.mean() * 100:.2f}%)"
        )

        min_dd_by_trade = paths_df.groupby("TradeID")["DrawdownFromPeak"].min()
        expected_dd = check_recon.set_index("TradeID")["MaxDrawdownDuringHold"]
        dd_match = np.isclose(
            min_dd_by_trade.reindex(expected_dd.index).values,
            expected_dd.values,
            rtol=RETURN_RTOL,
            atol=1e-6,
        )
        quality["min_drawdown_from_peak_vs_MaxDrawdownDuringHold"] = (
            f"{dd_match.sum():,} / {len(expected_dd):,} match ({dd_match.mean() * 100:.2f}%)"
        )

        quality["day0_cum_return_is_zero"] = (
            f"{(paths_df[paths_df['DayIndex'] == 0]['CumReturnFromEntry'].abs() < 1e-12).all()}"
        )

        dup = paths_df.duplicated(subset=["TradeID", "DayIndex"]).sum()
        quality["duplicate_trade_day_rows"] = f"{dup} (expect 0)"

        quality["status"] = (
            "PASS"
            if entry_match.all()
            and exit_match.all()
            and gross_match.all()
            and dd_match.all()
            and dup == 0
            else "REVIEW — see mismatches above"
        )

    write_validation_report(trades, paths_df, missing, quality)
    print(f" Saved -> {VALIDATION_OUT}")

    print(f"\n Paths reconstructed : {paths_df['TradeID'].nunique() if len(paths_df) else 0:,}")
    print(f" Missing             : {len(missing):,}")
    print(f" Quality status      : {quality.get('status', 'N/A')}")
    print("=" * 65)


if __name__ == "__main__":
    main()
