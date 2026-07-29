# pipeline_core.py

"""Core back‑test implementation (business logic).

This module contains the full functionality that was originally in
`portfolio_pipeline.py`.  It is deliberately kept separate so that the
`portfolio_pipeline` module can act purely as an orchestration layer.

All functions are unchanged to guarantee identical runtime behaviour.
"""

import json
import warnings
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Core components
from eval_engine import (
    PredictionAdapter,
    ValidationLayer,
    PortfolioConstructor,
    ModelAgnosticSimulator,
)
from portfolio_engine import PortfolioEngine

# ----------------------------------------------------------------------------
# Singleton PortfolioEngine – shared across the entire application
# ----------------------------------------------------------------------------
engine = PortfolioEngine()  # shared instance, can be used by callers if desired

# Global configuration constants (mirroring original step4_backtest defaults)
HOLD_DAYS = 5
MAX_POSITIONS = 10
POSITION_SIZE = 0.10
BROKERAGE = 0.001
SLIPPAGE = 0.002
TOTAL_COST = BROKERAGE + SLIPPAGE
STARTING_CAPITAL = 100_000

# ----------------------------------------------------------------------------
# Helper utilities (mirrored from original implementation)
# ----------------------------------------------------------------------------

def load_price_series(data_dir: str = "data") -> dict:
    """Load actual price series from CSV files in *data_dir*.

    Returns a dict mapping ``ticker -> pd.Series`` where the series index is a
    ``pd.DatetimeIndex`` of close prices.
    """
    DATA_DIR = Path(data_dir)
    prices = {}
    print("Loading actual price data for return calculation...")
    if not DATA_DIR.exists():
        print("Data directory not found. Please ensure price CSVs exist in 'data/'")
        return prices
    for f in DATA_DIR.glob("*.csv"):
        try:
            p = pd.read_csv(f, index_col=0)
            p.index = pd.to_datetime(p.index)
            if "Close" in p.columns or "Adj Close" in p.columns:
                col = "Adj Close" if "Adj Close" in p.columns else "Close"
                prices[f.stem] = p[col]
        except Exception:
            pass
    return prices


def compute_hold_path_metrics(hold_prices, entry_price, net_return):
    """Path analytics for a fixed hold window.

    Returns a dict with max gain, max drawdown, adverse excursion, etc.
    """
    hold = np.asarray(hold_prices, dtype=float)
    if len(hold) < 2 or entry_price <= 0:
        return None
    cum_ret = hold / entry_price - 1.0
    day_ret = np.diff(hold) / hold[:-1]
    running_max = np.maximum.accumulate(cum_ret)
    drawdowns = cum_ret - running_max
    max_gain = float(cum_ret.max())
    max_dd = float(drawdowns.min())
    mae = float(cum_ret.min())
    best_day = float(day_ret.max()) if len(day_ret) else 0.0
    worst_day = float(day_ret.min()) if len(day_ret) else 0.0
    was_profitable_intraday = max_gain > 0
    loser_but_green = net_return < 0 and was_profitable_intraday
    return {
        "MaxGainDuringHold": max_gain,
        "MaxDrawdownDuringHold": max_dd,
        "MaxAdverseExcursion": mae,
        "BestDayReturn": best_day,
        "WorstDayReturn": worst_day,
        "HitPlus2Pct": int(max_gain >= 0.02),
        "HitPlus3Pct": int(max_gain >= 0.03),
        "HitPlus5Pct": int(max_gain >= 0.05),
        "WasProfitableIntraday": int(was_profitable_intraday),
        "LoserButProfitableIntraday": int(loser_but_green),
    }


def print_path_analytics_v2(trades_df, hold_days):
    n = len(trades_df)
    losers = trades_df[trades_df['NetReturn'] < 0]
    n_losers = len(losers)
    print("\n" + "=" * 65)
    print(" PATH ANALYTICS (V2)")
    print("=" * 65)
    print(f"\n Hold period: {hold_days} trading days (entry/exit rules unchanged)")
    print(" Path metrics use gross prices; NetReturn still applies costs at exit.")
    print("\n Milestone hit rates (touched before exit):")
    for label, col in [('+2%', 'HitPlus2Pct'), ('+3%', 'HitPlus3Pct'), ('+5%', 'HitPlus5Pct')]:
        count = int(trades_df[col].sum())
        pct = count / n * 100
        print(f"   Hit {label:>4}  : {count:>6,} / {n:,}  ({pct:5.1f}%)")
    n_loser_green = int(trades_df['LoserButProfitableIntraday'].sum())
    print(f"\n Losing trades profitable at some point during hold:")
    print(f"   Losing trades (at exit)     : {n_losers:,}")
    print(f"   Green intraday, red at exit : {n_loser_green:,}")
    if n_losers > 0:
        print(f"   Share of losers             : {n_loser_green / n_losers * 100:5.1f}%")
    print(f"   Share of all trades         : {n_loser_green / n * 100:5.1f}%")
    print("\n Path distribution (per trade):")
    print(f"   {'Metric':<28} {'Mean':>9} {'Median':>9}")
    print(f"   {'-'*48}")
    for col in ['MaxGainDuringHold', 'MaxDrawdownDuringHold', 'BestDayReturn', 'WorstDayReturn']:
        s = trades_df[col] * 100
        print(f"   {col:<28} {s.mean():>+8.2f}% {s.median():>+8.2f}%")
    hit_2 = trades_df['HitPlus2Pct'].mean() * 100
    print("\n Note: model target is +2% within 5 days; "
          f"{hit_2:.1f}% of trades touched +2% at any point during the hold.")
    return build_path_analytics_summary(trades_df, hold_days)


def categorize_trade(row):
    if row['NetReturn'] > 0:
        return 'Winner'
    elif row['HitPlus2Pct'] == 1:
        return 'Prediction Success, Financial Loss'
    else:
        return 'Failed Prediction'


def print_prediction_quality_analysis(trades_df):
    n = int(len(trades_df))
    n_winners = int((trades_df['NetReturn'] > 0).sum())
    n_pred_success = int((trades_df['HitPlus2Pct'] == 1).sum())
    n_pred_and_winner = int(((trades_df['NetReturn'] > 0) & (trades_df['HitPlus2Pct'] == 1)).sum())
    n_pred_loss = int(((trades_df['NetReturn'] < 0) & (trades_df['HitPlus2Pct'] == 1)).sum())
    n_pred_failed = int(((trades_df['NetReturn'] < 0) & (trades_df['HitPlus2Pct'] == 0)).sum())
    pred_success_rate = n_pred_success / n * 100 if n > 0 else 0.0
    financial_win_rate = n_winners / n * 100 if n > 0 else 0.0
    avg_max_gain = trades_df['MaxGainDuringHold'].mean() * 100
    median_max_gain = trades_df['MaxGainDuringHold'].median() * 100
    print("\n" + "=" * 65)
    print(" PREDICTION QUALITY ANALYSIS")
    print("=" * 65)
    print(f"\n Total trades                          : {n:,}")
    print(f" Financial winners                    : {n_winners:,} ({financial_win_rate:.1f}%)")
    print(f" Prediction successes (+2% touched)   : {n_pred_success:,} ({pred_success_rate:.1f}%)")
    print(f" Prediction success + financial win   : {n_pred_and_winner:,}")
    print(f" Prediction success + financial loss  : {n_pred_loss:,}")
    print(f" Failed predictions                   : {n_pred_failed:,}")
    print(f"\n Prediction success rate              : {pred_success_rate:.1f}%")
    print(f" Financial win rate                   : {financial_win_rate:.1f}%")
    print(f" Average MaxGainDuringHold            : {avg_max_gain:+.2f}%")
    print(f" Median MaxGainDuringHold             : {median_max_gain:+.2f}%")
    return {
        'total_trades': n,
        'financial_winners': n_winners,
        'financial_win_rate': financial_win_rate,
        'prediction_successes': n_pred_success,
        'prediction_success_rate': pred_success_rate,
        'pred_success_and_winner': n_pred_and_winner,
        'pred_success_and_loss': n_pred_loss,
        'failed_predictions': n_pred_failed,
        'avg_max_gain_during_hold': avg_max_gain,
        'median_max_gain_during_hold': median_max_gain,
    }


def build_path_analytics_summary(trades_df, hold_days):
    n = int(len(trades_df))
    losers = trades_df[trades_df['NetReturn'] < 0]
    n_losers = int(len(losers))
    n_loser_green = int(trades_df['LoserButProfitableIntraday'].sum())
    def _rate(col):
        return float(trades_df[col].mean()) if n else 0.0
    def _count(col):
        return int(trades_df[col].sum())
    return {
        'hold_days': hold_days,
        'n_trades': n,
        'milestone_hit_rate': {
            'plus_2pct': _rate('HitPlus2Pct'),
            'plus_3pct': _rate('HitPlus3Pct'),
            'plus_5pct': _rate('HitPlus5Pct'),
        },
        'milestone_hit_count': {
            'plus_2pct': _count('HitPlus2Pct'),
            'plus_3pct': _count('HitPlus3Pct'),
            'plus_5pct': _count('HitPlus5Pct'),
        },
        'losers_profitable_intraday': {
            'losing_trades_at_exit': n_losers,
            'green_intraday_red_at_exit': n_loser_green,
            'pct_of_losers': n_loser_green / n_losers if n_losers else 0.0,
            'pct_of_all_trades': n_loser_green / n if n else 0.0,
        },
        'path_distribution': {
            'max_gain_during_hold': {
                'mean': float(trades_df['MaxGainDuringHold'].mean()),
                'median': float(trades_df['MaxGainDuringHold'].median()),
            },
            'max_drawdown_during_hold': {
                'mean': float(trades_df['MaxDrawdownDuringHold'].mean()),
                'median': float(trades_df['MaxDrawdownDuringHold'].median()),
            },
            'best_day_return': {
                'mean': float(trades_df['BestDayReturn'].mean()),
                'median': float(trades_df['BestDayReturn'].median()),
            },
            'worst_day_return': {
                'mean': float(trades_df['WorstDayReturn'].mean()),
                'median': float(trades_df['WorstDayReturn'].median()),
            },
        },
    }


def build_trade_df(signals, prices):
    trades = []
    for _, row in signals.iterrows():
        ticker = row['ticker']
        entry_date = row['Date']
        if ticker not in prices:
            continue
        stock_prices = prices[ticker]
        future_dates = stock_prices[stock_prices.index > entry_date]
        if len(future_dates) < HOLD_DAYS + 1:
            continue
        hold_prices = future_dates.iloc[0:HOLD_DAYS + 1]
        entry_price = hold_prices.iloc[0]
        exit_price = hold_prices.iloc[HOLD_DAYS]
        gross_return = (exit_price - entry_price) / entry_price
        net_return = gross_return - TOTAL_COST
        path_metrics = compute_hold_path_metrics(hold_prices.values, entry_price, net_return)
        if path_metrics is None:
            continue
        trades.append({
            'Date': future_dates.index[0],
            'SignalDate': entry_date,
            'Ticker': ticker,
            'Confidence': row['xg_proba'],
            'PredReturn': row.get('pred_return', np.nan),
            'EntryPrice': entry_price,
            'ExitPrice': exit_price,
            'GrossReturn': gross_return,
            'NetReturn': net_return,
            'Won': int(net_return > 0),
            **path_metrics,
        })
    return pd.DataFrame(trades)


def get_position_size(confidence):
    if confidence >= 0.85:
        return 0.15
    if confidence >= 0.80:
        return 0.125
    return 0.10


def simulate_portfolio(trades_df, prices, rank_by_pred_return=False):
    cash = STARTING_CAPITAL
    locked_cash = 0.0
    realized_pnl = 0.0
    portfolio_history = []
    open_positions = []
    entry_buckets = {}
    max_exit_date = trades_df['Date'].max()
    for date, day_trades in trades_df.groupby('Date'):
        if rank_by_pred_return and 'PredReturn' in day_trades.columns:
            entry_buckets[date] = day_trades.sort_values('PredReturn', ascending=False).head(MAX_POSITIONS)
        else:
            entry_buckets[date] = day_trades.sort_values('Confidence', ascending=False).head(MAX_POSITIONS)
    for date, day_trades in entry_buckets.items():
        day_trades = day_trades.copy()
        for idx, t in day_trades.iterrows():
            price_index = prices[t['Ticker']].index
            pos = price_index.get_indexer([t['Date']])[0]
            exit_date = price_index[pos + HOLD_DAYS]
            max_exit_date = max(max_exit_date, exit_date)
            day_trades.loc[idx, 'ExitDate'] = exit_date
        entry_buckets[date] = day_trades
    calendar_dates = sorted({d for ticker in trades_df['Ticker'].unique() if ticker in prices for d in prices[ticker].index})
    calendar_dates = [d for d in calendar_dates if d >= trades_df['Date'].min() and d <= max_exit_date]
    for today in calendar_dates:
        exits = [p for p in open_positions if p['ExitDate'] == today]
        for pos in exits:
            pnl = pos['LockedCash'] * pos['NetReturn']
            cash += pos['LockedCash'] + pnl
            locked_cash -= pos['LockedCash']
            realized_pnl += pnl
            open_positions.remove(pos)
        if today in entry_buckets and len(open_positions) < MAX_POSITIONS:
            for _, t in entry_buckets[today].iterrows():
                if len(open_positions) >= MAX_POSITIONS:
                    break
                available_cash = cash
                if available_cash <= 0:
                    break
                position_size = get_position_size(t['Confidence'])
                locked_amount = min(
                    available_cash,
                    (cash + sum(get_price_on_date(prices[pos['Ticker']], today) * pos['Quantity'] for pos in open_positions)) * position_size,
                )
                if locked_amount <= 0:
                    break
                quantity = locked_amount / t['EntryPrice']
                open_positions.append({
                    'Ticker': t['Ticker'],
                    'EntryDate': t['Date'],
                    'ExitDate': t['ExitDate'],
                    'EntryPrice': t['EntryPrice'],
                    'ExitPrice': t['ExitPrice'],
                    'Quantity': quantity,
                    'LockedCash': locked_amount,
                    'NetReturn': t['NetReturn'],
                    'Confidence': t['Confidence'],
                })
                cash -= locked_amount
                locked_cash += locked_amount
        unrealized_value = 0.0
        for pos in open_positions:
            current_price = get_price_on_date(prices[pos['Ticker']], today)
            if current_price is None:
                current_price = pos['EntryPrice']
            unrealized_value += pos['Quantity'] * current_price
        total_value = cash + unrealized_value
        portfolio_history.append({
            'Date': today,
            'Cash': cash,
            'LockedCash': locked_cash,
            'UnrealizedValue': unrealized_value,
            'TotalValue': total_value,
            'PositionsOpen': len(open_positions),
        })
    port_df = pd.DataFrame(portfolio_history)
    if len(port_df) > 0:
        port_df['Value'] = port_df['TotalValue']
        port_df['Drawdown'] = port_df['TotalValue'] / port_df['TotalValue'].cummax() - 1
        total_return = (port_df['TotalValue'].iloc[-1] - STARTING_CAPITAL) / STARTING_CAPITAL * 100
        max_dd = port_df['Drawdown'].min() * 100
    else:
        total_return = 0.0
        max_dd = 0.0
    return port_df, total_return, max_dd


def get_price_on_date(price_series, date):
    if date in price_series.index:
        return float(price_series.loc[date])
    prior = price_series[price_series.index < date]
    if len(prior) == 0:
        return None
    return float(prior.iloc[-1])

# ----------------------------------------------------------------------------
# Main orchestration function – thin wrapper for the legacy Step‑4 back‑test
# ----------------------------------------------------------------------------

def run_pipeline():
    """Execute the full back‑test exactly as ``step4_backtest.py`` originally did.

    The function prints progress information, writes the same output files and
    generates the equity‑curve chart.  It returns the portfolio DataFrame, the
    total return and the max drawdown for programmatic use.
    """
    df = pd.read_csv('test_predictions.csv')
    df['Date'] = pd.to_datetime(df['Date'])
    prices = load_price_series()
    CONFIDENCE_THRESHOLDS = [0.55, 0.60, 0.65, 0.70, 0.75]
    summary_rows = []
    baseline_trades_df = None
    baseline_threshold = 0.75
    for threshold in CONFIDENCE_THRESHOLDS:
        print(f"\n Threshold {threshold*100:.0f}%")
        signals = df[df['xg_proba'] >= threshold].copy()
        signals = signals.sort_values('Date')
        print(f" Total signals generated : {len(signals):,}")
        print(f" Unique stocks           : {signals['ticker'].nunique():,}")
        trades_df = build_trade_df(signals, prices)
        print(f" Trades simulated        : {len(trades_df):,}")
        if len(trades_df) == 0:
            print(" WARNING: No trades simulated for this threshold.")
            summary_rows.append({
                'Threshold': threshold,
                'Signals': len(signals),
                'Trades': 0,
                'WinRate': 0.0,
                'AvgNetReturn': 0.0,
                'PortfolioReturn': 0.0,
                'MaxDrawdown': 0.0,
            })
            continue
        win_rate = trades_df['Won'].mean() * 100
        avg_ret = trades_df['NetReturn'].mean() * 100
        rank_by_pred = abs(threshold - baseline_threshold) < 1e-9
        port_df, total_return, max_dd = simulate_portfolio(trades_df, prices, rank_by_pred_return=rank_by_pred)
        print(f"   Win rate         : {win_rate:.1f}%")
        print(f"   Avg net return   : {avg_ret:+.2f}% per trade")
        print(f"   Portfolio return : {total_return:+.1f}%")
        print(f"   Max drawdown     : {max_dd:+.1f}%")
        summary_rows.append({
            'Threshold': threshold,
            'Signals': len(signals),
            'Trades': len(trades_df),
            'WinRate': win_rate,
            'AvgNetReturn': avg_ret,
            'PortfolioReturn': total_return,
            'MaxDrawdown': max_dd,
        })
        if abs(threshold - baseline_threshold) < 1e-9:
            baseline_trades_df = trades_df
    if baseline_trades_df is None:
        print("ERROR: No baseline trades simulated for 75% threshold.")
        exit()
    trades_df = baseline_trades_df
    trades_df['PredictionSuccess'] = (trades_df['HitPlus2Pct'] == 1).astype(int)
    trades_df['TradeCategory'] = trades_df.apply(categorize_trade, axis=1)
    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv('threshold_sweep_summary.csv', index=False)
    print(f"\nThreshold sweep summary saved -> threshold_sweep_summary.csv")
    print(f"\n{'='*65}\n PERFORMANCE METRICS\n{'='*65}\n")
    win_rate = trades_df['Won'].mean() * 100
    avg_ret = trades_df['NetReturn'].mean() * 100
    med_ret = trades_df['NetReturn'].median() * 100
    total_ret = trades_df['NetReturn'].sum() * 100
    best = trades_df['NetReturn'].max() * 100
    worst = trades_df['NetReturn'].min() * 100
    print(f"   Total trades     : {len(trades_df):,}")
    print(f"   Win rate         : {win_rate:.1f}%")
    print(f"   Avg net return   : {avg_ret:+.2f}% per trade")
    print(f"   Median return    : {med_ret:+.2f}% per trade")
    print(f"   Best trade       : {best:+.2f}%")
    print(f"   Worst trade      : {worst:+.2f}%")
    print(f"\n By confidence level:\n   {'Confidence':>12} {'Trades':>8} {'Win%':>7} {'Avg Ret':>9}\n   {'-'*40}")
    for lo, hi in [(0.60, 0.65), (0.65, 0.70), (0.70, 0.75), (0.75, 1.01)]:
        sub = trades_df[(trades_df['Confidence'] >= lo) & (trades_df['Confidence'] < hi)]
        if len(sub) < 5:
            continue
        wr = sub['Won'].mean() * 100
        ar = sub['NetReturn'].mean() * 100
        print(f"   {lo:.0%} - {hi:.0%}    {len(sub):>7,}  {wr:>6.1f}%  {ar:>+8.2f}%")
    trades_df['Month'] = trades_df['Date'].dt.to_period('M')
    monthly = trades_df.groupby('Month').agg(
        Trades=('NetReturn', 'count'),
        WinRate=('Won', 'mean'),
        AvgReturn=('NetReturn', 'mean'),
    ).reset_index()
    print(f"\n Monthly breakdown (last 6 months):\n   {'Month':>8} {'Trades':>8} {'Win%':>7} {'Avg Ret':>9}\n   {'-'*36}")
    for _, r in monthly.tail(6).iterrows():
        print(f"   {str(r['Month']):>8} {r['Trades']:<8.0f} {r['WinRate']*100:>6.1f}% {r['AvgReturn']*100:>+8.2f}%")
    path_analytics_summary = print_path_analytics_v2(trades_df, HOLD_DAYS)
    pred_quality_summary = print_prediction_quality_analysis(trades_df)
    print(f"\n Portfolio Simulation (Rs. {STARTING_CAPITAL:,.0f} starting capital):\n")
    port_df, total_return, max_dd = simulate_portfolio(trades_df, prices, rank_by_pred_return=True)
    if len(port_df) > 0:
        portfolio_val = port_df['TotalValue'].iloc[-1]
        print(f"   Starting capital   : Rs. {STARTING_CAPITAL:>10,.0f}")
        print(f"   Final value        : Rs. {portfolio_val:>10,.0f}")
        print(f"   Total return       : {total_return:>+8.1f}%")
        print(f"   Max drawdown       : {max_dd:>+8.1f}%")
        print(f"   Test period        : {port_df['Date'].min().date()} -> {port_df['Date'].max().date()}")
        if len(port_df) > 5:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7))
            fig.suptitle('Stock ML Strategy — Backtest Results', fontsize=14, fontweight='bold')
            ax1.plot(port_df['Date'], port_df['Value'], color='#00C896', linewidth=2)
            ax1.axhline(y=STARTING_CAPITAL, color='gray', linestyle='--', alpha=0.5)
            ax1.set_title('Portfolio Value Over Time')
            ax1.set_ylabel('Portfolio Value (Rs.)')
            ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'Rs. {x:,.0f}'))
            ax1.grid(True, alpha=0.3)
            ax2.fill_between(port_df['Date'], port_df['Drawdown']*100, 0, color='#FF4444', alpha=0.6)
            ax2.set_title('Drawdown %')
            ax2.set_ylabel('Drawdown %')
            ax2.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig('backtest_results.png', dpi=150, bbox_inches='tight')
            print(f"\n   Chart saved -> backtest_results.png")
            plt.close()
    trades_df.to_csv('backtest_trades.csv', index=False)
    with open('backtest_analytics_v2.json', 'w', encoding='utf-8') as f:
        json.dump(path_analytics_summary, f, indent=2)
    if len(port_df) > 0:
        port_df.to_csv('portfolio_history.csv', index=False)
    print("\n" + "="*65)
    print("  BACKTEST COMPLETE")
    print("="*65)
    print("  Files saved:\n    backtest_trades.csv        <- all individual trades (incl. V2 path columns)\n    backtest_analytics_v2.json <- path analytics summary\n    portfolio_history.csv      <- day-by-day portfolio value\n    backtest_results.png       <- equity curve chart\n")
    print("  Next: Run step5_live_scanner.py (run this every morning)")
    print("="*65)
    return port_df, total_return, max_dd

if __name__ == "__main__":
    run_pipeline()
