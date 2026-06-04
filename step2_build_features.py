#!/usr/bin/env python3
"""
STEP 2: Build ML features from raw price/volume data.
Features are the same concept as our football model:
  - momentum = team form
  - volume spike = unusual activity
  - RSI = overbought/oversold signal
  - etc.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

DATA_DIR  = Path('data')
OUT_FILE  = Path('features.csv')

print("="*60)
print(" STEP 2: Building ML Features")
print("="*60)

def compute_features(df, ticker):
    """
    Build features for every trading day.
    For each day, we only use data BEFORE that day (no lookahead).
    """
    df = df.copy()
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    # ── Price features ──────────────────────────────────────────
    # Returns
    df['ret_1d']  = df['Close'].pct_change(1)
    df['ret_3d']  = df['Close'].pct_change(3)
    df['ret_5d']  = df['Close'].pct_change(5)
    df['ret_10d'] = df['Close'].pct_change(10)
    df['ret_20d'] = df['Close'].pct_change(20)

    # Moving averages
    df['ma5']   = df['Close'].rolling(5).mean()
    df['ma10']  = df['Close'].rolling(10).mean()
    df['ma20']  = df['Close'].rolling(20).mean()
    df['ma50']  = df['Close'].rolling(50).mean()

    # Price vs MA (is stock above or below its average?)
    df['price_vs_ma5']  = (df['Close'] - df['ma5'])  / df['ma5']
    df['price_vs_ma20'] = (df['Close'] - df['ma20']) / df['ma20']
    df['price_vs_ma50'] = (df['Close'] - df['ma50']) / df['ma50']

    # MA crossovers (momentum signal)
    df['ma5_vs_ma20']  = (df['ma5']  - df['ma20']) / df['ma20']
    df['ma10_vs_ma50'] = (df['ma10'] - df['ma50']) / df['ma50']

    # Momentum acceleration
    df['momentum_acceleration'] = df['ret_5d'] - df['ret_10d']

    # ── RSI (overbought/oversold) ────────────────────────────────
    delta = df['Close'].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, np.nan)
    df['rsi14'] = 100 - (100 / (1 + rs))
    df['rsi_normalized'] = (df['rsi14'] - 50) / 50  # center at 0

    # ── Volatility features ─────────────────────────────────────
    df['volatility_5d']  = df['ret_1d'].rolling(5).std()
    df['volatility_20d'] = df['ret_1d'].rolling(20).std()

    # High-Low range as % of close (daily volatility)
    df['hl_range'] = (df['High'] - df['Low']) / df['Close']

    # ── Volume features ─────────────────────────────────────────
    df['vol_ma20']      = df['Volume'].rolling(20).mean()
    df['volume_ratio']  = df['Volume'] / df['vol_ma20']   # spike = >1.5
    df['volume_trend']  = df['Volume'].rolling(5).mean() / df['vol_ma20']

    # Relative volume (safe division by zero)
    df['relative_volume'] = np.where(df['vol_ma20'] > 0, df['Volume'] / df['vol_ma20'], np.nan)

    up_vol = df['Volume'].where(df['Close'] > df['Close'].shift(1), 0)
    down_vol = df['Volume'].where(df['Close'] < df['Close'].shift(1), 0)
    up_vol_10 = up_vol.rolling(10).sum()
    down_vol_10 = down_vol.rolling(10).sum()
    df['updown_vol_ratio_10'] = np.where(down_vol_10 > 0, up_vol_10 / down_vol_10, np.nan)

    # ── Bollinger Band position ──────────────────────────────────
    bb_mid = df['Close'].rolling(20).mean()
    bb_std = df['Close'].rolling(20).std()
    df['bb_position'] = (df['Close'] - bb_mid) / (2 * bb_std)  # -1 to +1

    # ── Trend strength ───────────────────────────────────────────
    # Count of up days in last 5/10 days
    df['up_days_5']  = (df['ret_1d'] > 0).rolling(5).sum()  / 5
    df['up_days_10'] = (df['ret_1d'] > 0).rolling(10).sum() / 10

    # ── Gap (open vs previous close) ────────────────────────────
    df['gap'] = (df['Open'] - df['Close'].shift(1)) / df['Close'].shift(1)

    # ── TARGETS: future 5-day return and binary up-2% flag ─────────
    df['future_ret_5d'] = df['Close'].shift(-5) / df['Close'] - 1
    df['ret_5d_net']    = df['future_ret_5d'] - 0.003
    df['target']        = (df['future_ret_5d'] > 0.02).astype(int)
    # 1 = stock will rise 2%+ in next 5 days
    # 0 = it won't

    df['ticker'] = ticker
    return df

# ── Load Nifty index features for market regime signals ───────────────────
BENCHMARK_DIR = Path('benchmark')
NIFTY_INDEX_FILE = BENCHMARK_DIR / 'NIFTY50.csv'
if NIFTY_INDEX_FILE.exists():
    nifty_df = pd.read_csv(NIFTY_INDEX_FILE, index_col=0)
    nifty_df.index = pd.to_datetime(nifty_df.index)
    nifty_df = nifty_df.sort_index()

    if 'Adj Close' in nifty_df.columns:
        nifty_df['Close'] = nifty_df['Adj Close']

    nifty_df['nifty_ret_5d']  = nifty_df['Close'].pct_change(5)
    nifty_df['nifty_ret_20d'] = nifty_df['Close'].pct_change(20)
    nifty_df['nifty_ma50']    = nifty_df['Close'].rolling(50).mean()
    nifty_df['nifty_above_ma50'] = (nifty_df['Close'] > nifty_df['nifty_ma50']).astype(int)

    nifty_features = nifty_df[['nifty_ret_5d', 'nifty_ret_20d', 'nifty_above_ma50']].copy()
    print('Added Relative Strength Features')
else:
    nifty_features = pd.DataFrame()

print('Added RelativeVolume feature')

# ── Process all stocks ───────────────────────────────────────────────────
all_features = []
csv_files    = sorted(DATA_DIR.glob("*.csv"))

print(f"\nProcessing {len(csv_files)} stocks...\n")

for i, f in enumerate(csv_files):
    ticker = f.stem
    try:
        df = pd.read_csv(f, index_col=0)
        # Handle column naming
        df.columns = [c.strip() for c in df.columns]
        if 'Adj Close' in df.columns:
            df['Close'] = df['Adj Close']

        required = ['Open','High','Low','Close','Volume']
        if not all(c in df.columns for c in required):
            continue

        df = df[required].dropna()
        if len(df) < 60:
            continue

        df_feat = compute_features(df, ticker)

        if not nifty_features.empty:
            df_feat = df_feat.merge(
                nifty_features,
                left_index=True,
                right_index=True,
                how='left'
            )

        # Relative strength vs Nifty
        if not nifty_features.empty:
            df_feat['rs_ret_5d']  = df_feat['ret_5d']  - df_feat['nifty_ret_5d']
            df_feat['rs_ret_20d'] = df_feat['ret_20d'] - df_feat['nifty_ret_20d']

        # Drop rows where we don't have enough history
        feature_cols = [c for c in df_feat.columns if c not in
                        ['ticker','target','future_ret_5d','Open','High','Low','Close','Volume']]
        df_feat = df_feat.dropna(subset=feature_cols + ['target'])
        all_features.append(df_feat)

        if (i+1) % 20 == 0:
            print(f"  {i+1}/{len(csv_files)} processed")

    except Exception as e:
        print(f"  ERROR {ticker}: {e}")

print('Added updown_vol_ratio_10')

# ── Combine and save ─────────────────────────────────────────────────────
full = pd.concat(all_features, ignore_index=False)
full = full.reset_index().rename(columns={'index':'Date'})

# ── Add cross-sectional momentum rank feature ────────────────────────────
# For each date, rank all stocks by their 20-day return and convert to percentile
print("\nAdding cross-sectional momentum rank (cs_rank_20d)...")

cs_rank_list = []

for date in full['Date'].unique():
    date_data = full[full['Date'] == date].copy()
    valid = date_data.dropna(subset=['ret_20d'])
    
    if len(valid) > 1:
        # Rank by ret_20d (higher = better)
        ranks = valid['ret_20d'].rank(method='average')
        # Convert to percentile: 0 to 1 range
        percentile = (ranks - 1) / (len(ranks) - 1)
        
        cs_rank_result = pd.DataFrame({
            'Date': date,
            'ticker': valid['ticker'].values,
            'cs_rank_20d': percentile.values
        })
        cs_rank_list.append(cs_rank_result)
    elif len(valid) == 1:
        # Single stock on date = rank 0.5
        cs_rank_result = pd.DataFrame({
            'Date': [date],
            'ticker': valid['ticker'].values,
            'cs_rank_20d': [0.5]
        })
        cs_rank_list.append(cs_rank_result)

if cs_rank_list:
    cs_rank_df = pd.concat(cs_rank_list, ignore_index=True)
    full = full.merge(cs_rank_df, on=['Date', 'ticker'], how='left')
    print(f"  Added cs_rank_20d feature")
    print(f"  Non-null values: {full['cs_rank_20d'].notna().sum()} / {len(full)} ({full['cs_rank_20d'].notna().sum()/len(full)*100:.1f}%)")
else:
    print("  WARNING: Could not compute cs_rank_20d")

full.to_csv(OUT_FILE, index=False)

feature_cols = [c for c in full.columns if c not in
                ['Date','ticker','target','future_ret_5d','Open','High','Low','Close','Volume']]

print(f"\n{'='*60}")
print(f" DONE")
print(f"{'='*60}")
print(f" Stocks processed    : {full['ticker'].nunique()}")
print(f" Total rows          : {len(full):,}")
print(f" Features per stock  : {len(feature_cols)}")
print(f" Date range          : {str(full['Date'].min())[:10]} -> {str(full['Date'].max())[:10]}")
print(f" Target distribution : {full['target'].value_counts().to_dict()}")
print(f"\n Target = 1 means stock will rise 2%+ in next 5 days")
print(f" Base rate           : {full['target'].mean()*100:.1f}% of days qualify")
print(f"\n Saved -> features.csv")
print(f" Next: Run step3_train_model.py")
print(f"{'='*60}")
