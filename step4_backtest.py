#!/usr/bin/env python3
"""
STEP 4: Backtest the ML strategy with realistic costs.
Uses test set predictions from Step 3.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

print("="*65)
print(" STEP 4: Strategy Backtest")
print("="*65)

# ── Load predictions ─────────────────────────────────────────────────────
df = pd.read_csv('test_predictions.csv')
df['Date'] = pd.to_datetime(df['Date'])

# Load price data to get actual future returns
DATA_DIR = Path('data')

print("\nLoading actual price data for return calculation...")
prices = {}
for f in DATA_DIR.glob("*.csv"):
    try:
        p = pd.read_csv(f, index_col=0)
        p.index = pd.to_datetime(p.index)
        if 'Close' in p.columns or 'Adj Close' in p.columns:
            col = 'Adj Close' if 'Adj Close' in p.columns else 'Close'
            prices[f.stem] = p[col]
    except:
        pass

# ── Strategy parameters ──────────────────────────────────────────────────
CONFIDENCE_THRESHOLD = 0.60   # only trade when model is 60%+ confident
HOLD_DAYS            = 5      # hold for 5 trading days
MAX_POSITIONS        = 10     # max 10 stocks at once
POSITION_SIZE        = 0.10   # 10% of portfolio per stock
BROKERAGE            = 0.001  # 0.1% per trade (Zerodha approx)
SLIPPAGE             = 0.002  # 0.2% slippage (realistic for mid-caps)
TOTAL_COST           = BROKERAGE + SLIPPAGE

STARTING_CAPITAL     = 100_000  # ₹1,00,000

print(f"\n Strategy parameters:")
print(f"   Confidence threshold : {CONFIDENCE_THRESHOLD*100:.0f}%")
print(f"   Hold period          : {HOLD_DAYS} trading days")
print(f"   Max positions        : {MAX_POSITIONS}")
print(f"   Position size        : {POSITION_SIZE*100:.0f}% of portfolio")
print(f"   Transaction cost     : {TOTAL_COST*100:.2f}% per trade (both sides)")
print(f"   Starting capital     : ₹{STARTING_CAPITAL:,.0f}")

# ── Simulate trades ───────────────────────────────────────────────────────
signals = df[df['signal'] == 1].copy()
signals = signals.sort_values('Date')

print(f"\n Total signals generated : {len(signals):,}")
print(f" Unique stocks           : {signals['ticker'].nunique()}")

trades = []

for _, row in signals.iterrows():
    ticker = row['ticker']
    entry_date = row['Date']

    if ticker not in prices:
        continue

    stock_prices = prices[ticker]

    # Find entry price (next day open approximated by close)
    future_dates = stock_prices[stock_prices.index > entry_date]
    if len(future_dates) < HOLD_DAYS + 1:
        continue

    entry_price = future_dates.iloc[0]
    exit_price  = future_dates.iloc[HOLD_DAYS]

    # Calculate return
    gross_return = (exit_price - entry_price) / entry_price
    net_return   = gross_return - TOTAL_COST  # subtract transaction costs

    trades.append({
        'Date':        entry_date,
        'Ticker':      ticker,
        'Confidence':  row['xg_proba'],
        'EntryPrice':  entry_price,
        'ExitPrice':   exit_price,
        'GrossReturn': gross_return,
        'NetReturn':   net_return,
        'Won':         int(net_return > 0)
    })

trades_df = pd.DataFrame(trades)
print(f" Trades simulated        : {len(trades_df):,}")

if len(trades_df) == 0:
    print("ERROR: No trades simulated. Check that data files are present.")
    exit()

# ── Performance metrics ───────────────────────────────────────────────────
print(f"\n{'='*65}")
print(f" PERFORMANCE METRICS")
print(f"{'='*65}")

win_rate   = trades_df['Won'].mean() * 100
avg_ret    = trades_df['NetReturn'].mean() * 100
med_ret    = trades_df['NetReturn'].median() * 100
total_ret  = trades_df['NetReturn'].sum() * 100
best       = trades_df['NetReturn'].max() * 100
worst      = trades_df['NetReturn'].min() * 100

print(f"\n Overall:")
print(f"   Total trades     : {len(trades_df):,}")
print(f"   Win rate         : {win_rate:.1f}%")
print(f"   Avg net return   : {avg_ret:+.2f}% per trade")
print(f"   Median return    : {med_ret:+.2f}% per trade")
print(f"   Best trade       : {best:+.2f}%")
print(f"   Worst trade      : {worst:+.2f}%")

# By confidence bucket
print(f"\n By confidence level:")
print(f"   {'Confidence':>12} {'Trades':>8} {'Win%':>7} {'Avg Ret':>9}")
print(f"   {'-'*40}")
for lo, hi in [(0.60,0.65),(0.65,0.70),(0.70,0.75),(0.75,1.01)]:
    sub = trades_df[(trades_df['Confidence']>=lo)&(trades_df['Confidence']<hi)]
    if len(sub) < 5: continue
    wr  = sub['Won'].mean()*100
    ar  = sub['NetReturn'].mean()*100
    print(f"   {lo:.0%} - {hi:.0%}    {len(sub):>7,}  {wr:>6.1f}%  {ar:>+8.2f}%")

# Monthly performance
trades_df['Month'] = trades_df['Date'].dt.to_period('M')
monthly = trades_df.groupby('Month').agg(
    Trades=('NetReturn','count'),
    WinRate=('Won','mean'),
    AvgReturn=('NetReturn','mean')
).reset_index()

print(f"\n Monthly breakdown (last 6 months):")
print(f"   {'Month':>8} {'Trades':>8} {'Win%':>7} {'Avg Ret':>9}")
print(f"   {'-'*36}")
for _, r in monthly.tail(6).iterrows():
    print(f"   {str(r['Month']):>8} {r['Trades']:>8.0f} {r['WinRate']*100:>6.1f}% {r['AvgReturn']*100:>+8.2f}%")

# ── Portfolio simulation ──────────────────────────────────────────────────
print(f"\n Portfolio Simulation (₹{STARTING_CAPITAL:,.0f} starting capital):")

portfolio_val = STARTING_CAPITAL
portfolio_history = []

# Sort by date, simulate taking up to MAX_POSITIONS per day
for date, day_trades in trades_df.groupby('Date'):
    # Take top signals by confidence
    day_top = day_trades.sort_values('Confidence', ascending=False).head(MAX_POSITIONS)

    for _, t in day_top.iterrows():
        position_size = portfolio_val * POSITION_SIZE
        profit = position_size * t['NetReturn']
        portfolio_val += profit

    portfolio_history.append({'Date': date, 'Value': portfolio_val})

port_df = pd.DataFrame(portfolio_history)

if len(port_df) > 0:
    total_return = (portfolio_val - STARTING_CAPITAL) / STARTING_CAPITAL * 100
    peak         = port_df['Value'].max()
    port_df['Drawdown'] = port_df['Value'] / port_df['Value'].cummax() - 1
    max_dd       = port_df['Drawdown'].min() * 100

    print(f"   Starting capital   : ₹{STARTING_CAPITAL:>10,.0f}")
    print(f"   Final value        : ₹{portfolio_val:>10,.0f}")
    print(f"   Total return       : {total_return:>+8.1f}%")
    print(f"   Max drawdown       : {max_dd:>+8.1f}%")
    print(f"   Test period        : {trades_df['Date'].min().date()} -> {trades_df['Date'].max().date()}")

# ── Save outputs ──────────────────────────────────────────────────────────
trades_df.to_csv('backtest_trades.csv', index=False)
if len(port_df) > 0:
    port_df.to_csv('portfolio_history.csv', index=False)

# ── Plot equity curve ─────────────────────────────────────────────────────
if len(port_df) > 5:
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7))
    fig.suptitle('Stock ML Strategy — Backtest Results', fontsize=14, fontweight='bold')

    ax1.plot(port_df['Date'], port_df['Value'], color='#00C896', linewidth=2)
    ax1.axhline(y=STARTING_CAPITAL, color='gray', linestyle='--', alpha=0.5)
    ax1.set_title('Portfolio Value Over Time')
    ax1.set_ylabel('Portfolio Value (₹)')
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x,p: f'₹{x:,.0f}'))
    ax1.grid(True, alpha=0.3)

    ax2.fill_between(port_df['Date'], port_df['Drawdown']*100, 0,
                     color='#FF4444', alpha=0.6)
    ax2.set_title('Drawdown %')
    ax2.set_ylabel('Drawdown %')
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('backtest_results.png', dpi=150, bbox_inches='tight')
    print(f"\n   Chart saved -> backtest_results.png")
    plt.close()

print(f"""
{'='*65}
 BACKTEST COMPLETE
{'='*65}
 Files saved:
   backtest_trades.csv     ← all individual trades
   portfolio_history.csv   ← day-by-day portfolio value
   backtest_results.png    ← equity curve chart

 Next: Run step5_live_scanner.py (run this every morning)
{'='*65}
""")
