#!/usr/bin/env python3
"""
debug_backtest.py
Trace every stage of the backtest pipeline.
Writes DEBUG_BACKTEST.md with root-cause findings.
"""

import sys
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

ROOT       = Path(__file__).resolve().parent
PREDS_FILE = ROOT / "ranker_preds.csv"
DATA_DIR   = ROOT / "data"
REPORT_MD  = ROOT / "DEBUG_BACKTEST.md"

HOLD_DAYS         = 5
CONFIDENCE_THRESH = 0.75
TOTAL_COST        = 0.003

lines = []  # collect report lines

def log(s=""):
    print(s)
    lines.append(s)

def sep(title=""):
    log("=" * 65)
    if title:
        log(f"  {title}")
        log("=" * 65)

def chk(n, desc, count):
    tag = "OK" if count > 0 else "<<< ZERO - POSSIBLE CAUSE >>>"
    log(f"  [{n}] {desc}: {count:,}  [{tag}]")

# ─── STEP 1 ───────────────────────────────────────────────────────────────────
sep("STEP 1 - LOAD PREDICTION FILE")

if not PREDS_FILE.exists():
    log(f"  ERROR: {PREDS_FILE} does not exist!")
    sys.exit(1)

df = pd.read_csv(PREDS_FILE)
df["Date"] = pd.to_datetime(df["Date"])

log(f"  File            : {PREDS_FILE.name}")
log(f"  Shape           : {df.shape}")
log(f"  Columns         : {list(df.columns)}")
log(f"  Date range      : {df['Date'].min().date()} -> {df['Date'].max().date()}")
log(f"  Unique dates    : {df['Date'].nunique():,}")
log(f"  Unique tickers  : {df['ticker'].nunique():,}")

chk(1, "Total rows in ranker_preds.csv", len(df))

log("")
log("  Score statistics:")
for col in ["classifier_score", "ranker_score"]:
    if col in df.columns:
        s = df[col]
        log(f"    {col}: min={s.min():.4f}  max={s.max():.4f}  "
            f"mean={s.mean():.4f}  nulls={s.isna().sum()}")
        for thresh in [0.50, 0.55, 0.60, 0.65, 0.70, 0.75]:
            above = (s >= thresh).sum()
            log(f"      >= {thresh:.2f}: {above:,}")
    else:
        log(f"    {col}: NOT PRESENT")

# ─── STEP 2 ───────────────────────────────────────────────────────────────────
sep("STEP 2 - LOAD PRICE DATA")

prices = {}
failed = []
for f in DATA_DIR.glob("*.csv"):
    try:
        p = pd.read_csv(f, index_col=0)
        p.index = pd.to_datetime(p.index)
        if "Adj Close" in p.columns:
            prices[f.stem] = p["Adj Close"].sort_index()
        elif "Close" in p.columns:
            prices[f.stem] = p["Close"].sort_index()
        else:
            failed.append(f.name)
    except Exception as exc:
        failed.append(f"{f.name}: {exc}")

chk(2, "Tickers with price data loaded", len(prices))
if failed:
    log(f"  Failed files: {len(failed)}")
    for fn in failed[:5]:
        log(f"    {fn}")

# ─── STEP 3 ───────────────────────────────────────────────────────────────────
sep("STEP 3 - TICKER OVERLAP")

pred_tickers  = set(df["ticker"].unique())
price_tickers = set(prices.keys())
overlap       = pred_tickers & price_tickers
missing_price = pred_tickers - price_tickers

log(f"  Tickers in predictions : {len(pred_tickers):,}")
log(f"  Tickers in price data  : {len(price_tickers):,}")
log(f"  Overlap                : {len(overlap):,}")
log(f"  No price data for      : {len(missing_price):,}")
if missing_price:
    log(f"  Sample missing         : {sorted(missing_price)[:10]}")

chk(3, "Tickers with both predictions AND price data", len(overlap))

rows_with_price = df[df["ticker"].isin(price_tickers)]
chk("3b", "Prediction rows with matching price ticker", len(rows_with_price))

# ─── STEP 4 ───────────────────────────────────────────────────────────────────
sep("STEP 4 - CONFIDENCE THRESHOLD FILTER (classifier_score)")

if "classifier_score" in df.columns:
    for thresh in [0.50, 0.55, 0.60, 0.65, 0.70, 0.75]:
        above = (df["classifier_score"] >= thresh).sum()
        log(f"  classifier_score >= {thresh:.2f}: {above:,} rows")
    signals_75 = df[df["classifier_score"] >= CONFIDENCE_THRESH].copy()
else:
    log("  classifier_score column NOT FOUND!")
    signals_75 = pd.DataFrame()

chk(4, f"Signals after classifier_score >= {CONFIDENCE_THRESH}", len(signals_75))

# ─── STEP 5 ───────────────────────────────────────────────────────────────────
sep("STEP 5 - TRADE BUILDING (replicate build_trade_df logic per-filter)")

def build_trades_verbose(signals, prices, tag, score_col=None):
    skip_no_price  = 0
    skip_no_future = 0
    skip_bad_entry = 0
    assembled      = 0

    for _, row in signals.iterrows():
        ticker     = row["ticker"]
        entry_date = row["Date"]

        if ticker not in prices:
            skip_no_price += 1
            continue

        sp  = prices[ticker]
        fut = sp[sp.index > entry_date]

        if len(fut) < HOLD_DAYS + 1:
            skip_no_future += 1
            continue

        ep = float(fut.iloc[0])
        if ep <= 0:
            skip_bad_entry += 1
            continue

        assembled += 1

    log(f"  [{tag}] total signals       : {len(signals):,}")
    log(f"  [{tag}] skip (no price)     : {skip_no_price:,}")
    log(f"  [{tag}] skip (no future)    : {skip_no_future:,}")
    log(f"  [{tag}] skip (bad entry)    : {skip_bad_entry:,}")
    log(f"  [{tag}] assembled trades    : {assembled:,}")
    log("")
    return assembled

log("")
log("  [5a] Classifier score >= 0.75 signals through build_trade_df:")
n5a = build_trades_verbose(signals_75, prices, "5a", "classifier_score")
chk("5a", "Trades from classifier >= 0.75", n5a)

log("")
log("  [5b] Top-10/day classifier (no threshold) through build_trade_df:")
top10_clf = (
    rows_with_price
    .groupby("Date", group_keys=False)
    .apply(lambda g: g.nlargest(10, "classifier_score"))
    .reset_index(drop=False)  # keep Date as column
)
# If Date ended up as index after groupby, reset properly
if "Date" not in top10_clf.columns:
    top10_clf = top10_clf.reset_index()
n5b = build_trades_verbose(top10_clf, prices, "5b", "classifier_score")
chk("5b", "Trades from classifier top-10/day (no threshold)", n5b)

if "ranker_score" in df.columns:
    log("")
    log("  [5c] Top-10/day ranker (no threshold):")
    top10_rnk = (
        rows_with_price
        .groupby("Date", group_keys=False)
        .apply(lambda g: g.nlargest(10, "ranker_score"))
        .reset_index(drop=False)
    )
    if "Date" not in top10_rnk.columns:
        top10_rnk = top10_rnk.reset_index()
    n5c = build_trades_verbose(top10_rnk, prices, "5c", "ranker_score")
    chk("5c", "Trades from ranker top-10/day (no threshold)", n5c)

# ─── STEP 6 ───────────────────────────────────────────────────────────────────
sep("STEP 6 - DATE ALIGNMENT (sample ticker)")

if overlap:
    sample_tk = sorted(overlap)[0]
    ps        = prices[sample_tk]
    pred_d    = df[df["ticker"] == sample_tk]["Date"]

    log(f"  Sample ticker    : {sample_tk}")
    log(f"  Price range      : {ps.index.min().date()} -> {ps.index.max().date()}")
    log(f"  Pred  range      : {pred_d.min().date()} -> {pred_d.max().date()}")

    viable = sum(1 for d in pred_d if len(ps[ps.index > d]) >= HOLD_DAYS + 1)
    log(f"  Pred dates with >= {HOLD_DAYS+1} future pts: {viable} / {len(pred_d)}")

    if viable == 0:
        log("  *** DATE ALIGNMENT ISSUE: predictions fall at/after end of price data ***")

# ─── STEP 7 ───────────────────────────────────────────────────────────────────
sep("STEP 7 - COLUMN NAME COMPATIBILITY")

log("  Columns in ranker_preds.csv: " + str(list(df.columns)))
log("")

# ranker_backtest.build_trade_df_top_n produces {Date, ticker, pred_return}
# walkforward simulate_portfolio expects {Date, Ticker, Confidence, EntryPrice, ...}
produced = ["Date", "ticker", "pred_return"]
expected = ["Date", "Ticker", "Confidence", "EntryPrice", "ExitPrice", "NetReturn", "Won"]

log("  ranker_backtest.build_trade_df_top_n  produces : " + str(produced))
log("  walkforward.simulate_portfolio        expects  : " + str(expected))

col_mismatches = [c for c in expected if c not in produced]
log(f"  Missing columns for simulate_portfolio : {col_mismatches}")

if col_mismatches:
    log("")
    log("  *** COLUMN MISMATCH DETECTED ***")
    log("  The trade DataFrame assembled by ranker_backtest is INCOMPATIBLE")
    log("  with the simulate_portfolio function from walkforward_validation.")
    log("  simulate_portfolio_safe() wraps the call in try/except and returns")
    log("  (port={Drawdown:[0]}, 0.0, 0.0, 0.0, 0.0, 0) on ANY exception.")
    log("  Result: 0 trades, 0 CAGR, 0 Sharpe -- silently.")

# Check xg_proba
has_xg_proba    = "xg_proba" in df.columns
has_clf_score   = "classifier_score" in df.columns
log("")
log(f"  'xg_proba' in ranker_preds.csv       : {has_xg_proba}")
log(f"  'classifier_score' in ranker_preds   : {has_clf_score}")
if not has_xg_proba and has_clf_score:
    log("  walkforward.build_trade_df reads row['xg_proba'] at line 135.")
    log("  ranker_preds.csv does NOT have 'xg_proba'.")
    log("  -> Any code path that feeds ranker_preds.csv into build_trade_df will fail.")

# ─── STEP 8 ───────────────────────────────────────────────────────────────────
sep("STEP 8 - simulate_portfolio IMPORT TEST")

try:
    from walkforward_validation import simulate_portfolio, HOLD_DAYS as WF_HOLD
    log("  Import OK.")

    # Build a minimal fake trades_df missing Confidence/Ticker etc.
    fake = pd.DataFrame([{
        "Date": pd.Timestamp("2024-01-02"),
        "ticker": "FAKE",
        "pred_return": 0.5,
    }])
    log(f"  Fake trades columns: {list(fake.columns)}")
    try:
        simulate_portfolio(fake, {}, rank_by_pred_return=True)
        log("  simulate_portfolio ran without error (unexpected).")
    except Exception as exc:
        log(f"  simulate_portfolio raised: {type(exc).__name__}: {exc}")
        log("  -> simulate_portfolio_safe() in ranker_backtest CATCHES this and returns 0 trades.")

except Exception as exc:
    log(f"  Import failed: {exc}")

# ─── STEP 9 ───────────────────────────────────────────────────────────────────
sep("STEP 9 - WALKFORWARD REPORT METRICS SANITY CHECK")

wf_report = ROOT / "WALKFORWARD_REPORT.md"
if wf_report.exists():
    text = wf_report.read_text()
    log("  WALKFORWARD_REPORT.md exists.")
    # look for zero-trades indicators
    for kw in ["0 trades", "no trades", "Trades: 0", "Trades|0"]:
        if kw.lower() in text.lower():
            log(f"  Found '{kw}' in walkforward report.")
else:
    log("  WALKFORWARD_REPORT.md not found.")

# ─── STEP 10 - SUMMARY ────────────────────────────────────────────────────────
sep("STEP 10 - ROOT CAUSE SUMMARY")

issues = []

if len(overlap) == 0:
    issues.append(
        "CRITICAL: Zero tickers overlap between predictions and price data. "
        "No trades can ever be built."
    )

if not has_xg_proba and has_clf_score:
    issues.append(
        "CRITICAL (Column mismatch): ranker_preds.csv uses column name 'classifier_score' "
        "but walkforward_validation.build_trade_df reads row['xg_proba'] (line 135). "
        "KeyError -> simulate_portfolio_safe catches it -> returns 0 trades silently."
    )

if col_mismatches:
    issues.append(
        f"CRITICAL (Schema mismatch): ranker_backtest.build_trade_df_top_n produces "
        f"columns {{Date, ticker, pred_return}} but walkforward.simulate_portfolio "
        f"expects {expected}. Missing: {col_mismatches}. "
        f"The call fails inside simulate_portfolio_safe try/except -> 0 trades."
    )

if n5b == 0 and len(rows_with_price) > 0:
    issues.append(
        "CRITICAL (Date alignment): Even top-10/day with no threshold produces 0 trades. "
        "All prediction dates fall at or after the end of the price series -- "
        "there are no future price points for the hold window."
    )

if n5b > 0 and n5a == 0:
    issues.append(
        "WARNING: Top-10/day produces trades but confidence >= 0.75 produces none. "
        "The classifier score distribution never reaches 0.75 -- threshold is too high."
    )

if not issues:
    issues.append("No clear cause found -- all filters pass and trades are assembled.")

log("")
for i, iss in enumerate(issues, 1):
    log(f"  ISSUE {i}: {iss}")
    log("")

# ─── Write report ─────────────────────────────────────────────────────────────
report_text = "\n".join(lines)

md = "# DEBUG_BACKTEST Report\n\n"
md += "> Generated by `debug_backtest.py`  \n"
md += f"> Prediction file: `{PREDS_FILE.name}`  \n\n"

md += "## Quick-Reference Counts\n\n"
md += "| # | Checkpoint | Count |\n"
md += "|---|---|---|\n"
md += f"| 1  | Total rows in ranker_preds.csv | {len(df):,} |\n"
md += f"| 2  | Tickers with price data | {len(prices):,} |\n"
md += f"| 3  | Ticker overlap (preds ∩ prices) | {len(overlap):,} |\n"
md += f"| 3b | Prediction rows with matching price ticker | {len(rows_with_price):,} |\n"
md += f"| 4  | Signals after classifier_score >= 0.75 | {len(signals_75):,} |\n"
md += f"| 5a | Assembled trades (classifier >= 0.75) | {n5a:,} |\n"
md += f"| 5b | Assembled trades (classifier top-10/day) | {n5b:,} |\n"
md += "\n"

md += "## Root Cause(s)\n\n"
for i, iss in enumerate(issues, 1):
    md += f"### Issue {i}\n{iss}\n\n"

md += "---\n\n## Full Diagnostic Log\n\n```\n"
md += report_text
md += "\n```\n"

REPORT_MD.write_text(md, encoding="utf-8")
log(f"\nReport written -> {REPORT_MD.name}")
