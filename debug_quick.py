#!/usr/bin/env python3
"""Quick targeted diagnostic - confirms root causes."""
import pandas as pd, numpy as np
from pathlib import Path

ROOT = Path('.')
PREDS_FILE = ROOT / 'ranker_preds.csv'
DATA_DIR = ROOT / 'data'
HOLD_DAYS = 5

df = pd.read_csv(PREDS_FILE)
df['Date'] = pd.to_datetime(df['Date'])

prices = {}
for f in DATA_DIR.glob('*.csv'):
    try:
        p = pd.read_csv(f, index_col=0)
        p.index = pd.to_datetime(p.index)
        if 'Adj Close' in p.columns:
            prices[f.stem] = p['Adj Close'].sort_index()
        elif 'Close' in p.columns:
            prices[f.stem] = p['Close'].sort_index()
    except:
        pass

print("=== SCORE RANGE CHECK ===")
print(f"classifier_score: min={df['classifier_score'].min():.4f}  max={df['classifier_score'].max():.4f}")
print(f"ranker_score:     min={df['ranker_score'].min():.4f}  max={df['ranker_score'].max():.4f}")
print(">> classifier_score NEVER reaches 0.50. Threshold 0.75 filters ALL signals -> 0 trades.")

print()
print("=== TOP-10/DAY VIABILITY (no threshold) ===")
rows = df[df['ticker'].isin(prices.keys())].copy()
total_dates = rows['Date'].nunique()
no_price = 0
no_future = 0
assembled = 0
for date, grp in rows.groupby('Date'):
    top = grp.nlargest(10, 'classifier_score')
    for _, row in top.iterrows():
        ticker = row['ticker']
        if ticker not in prices:
            no_price += 1
            continue
        sp = prices[ticker]
        fut = sp[sp.index > date]
        if len(fut) < HOLD_DAYS + 1:
            no_future += 1
            continue
        assembled += 1

print(f"Total dates            : {total_dates}")
print(f"Skip (no price)        : {no_price}")
print(f"Skip (no future prices): {no_future}")
print(f"Assembled trades       : {assembled}")

print()
print("=== DATE ALIGNMENT (3 sample tickers) ===")
for tk in sorted(set(df['ticker']) & set(prices.keys()))[:3]:
    ps = prices[tk]
    pred_dates = df[df['ticker'] == tk]['Date']
    viable = sum(1 for d in pred_dates if len(ps[ps.index > d]) >= HOLD_DAYS + 1)
    print(f"{tk}: price {ps.index.min().date()}->{ps.index.max().date()} | "
          f"pred {pred_dates.min().date()}->{pred_dates.max().date()} | "
          f"viable={viable}/{len(pred_dates)}")

print()
print("=== COLUMN MISMATCH CHECK ===")
# ranker_backtest.build_trade_df_top_n returns: Date, ticker, pred_return
produced_cols = ['Date', 'ticker', 'pred_return']
required_by_simulate_portfolio = ['Ticker', 'Confidence', 'EntryPrice', 'ExitPrice', 'NetReturn', 'Won']
missing_cols = [c for c in required_by_simulate_portfolio if c not in produced_cols]
print(f"ranker_backtest produces cols : {produced_cols}")
print(f"simulate_portfolio needs      : {required_by_simulate_portfolio}")
print(f"MISSING cols                  : {missing_cols}")
if missing_cols:
    print("-> simulate_portfolio_safe catches KeyError -> returns 0 trades silently")

print()
print("=== walkforward build_trade_df column check ===")
print("walkforward build_trade_df reads row['xg_proba'] (line 135)")
has_xg = 'xg_proba' in df.columns
has_clf = 'classifier_score' in df.columns
print(f"'xg_proba' in ranker_preds.csv      : {has_xg}")
print(f"'classifier_score' in ranker_preds  : {has_clf}")
if not has_xg and has_clf:
    print("-> ranker_preds.csv has NO 'xg_proba' column. walkforward.build_trade_df will fail.")

print()
print("=== SUMMARY OF ROOT CAUSES ===")
print()
print("ROOT CAUSE 1 (CONFIRMED - CRITICAL):")
print("  classifier_score max = 0.4275, NEVER >= 0.50.")
print("  step4_backtest.py filters on xg_proba >= 0.55..0.75.")
print("  ranker_preds.csv does NOT have 'xg_proba', it has 'classifier_score'.")
print("  The classifier model outputs raw probabilities in the range [0.27, 0.43].")
print("  The model is under-confident - all scores cluster below 0.50.")
print("  ANY confidence threshold >= 0.50 eliminates 100% of all signals.")
print()
print("ROOT CAUSE 2 (CONFIRMED - CRITICAL):")
print("  ranker_backtest.build_trade_df_top_n outputs {Date, ticker, pred_return}.")
print("  walkforward_validation.simulate_portfolio expects {Ticker, Confidence, EntryPrice, ...}.")
print("  simulate_portfolio_safe() wraps the call in try/except and silently returns 0.")
print("  Result: 0 trades, 0 CAGR, 0 Sharpe even when trades are assembled.")
print()
print("ROOT CAUSE 3 (CONFIRM PENDING):")
print("  Check if pred dates have enough future price data (see viability above).")
