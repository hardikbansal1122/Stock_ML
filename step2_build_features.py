#!/usr/bin/env python3
"""
STEP 2: Build ML features from raw price/volume data.
Features are the same concept as our football model:
  - momentum = team form
  - volume spike = unusual activity
  - RSI = overbought/oversold signal
  - etc.
"""

import sys
from pathlib import Path
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from universe import load_universe, normalize_ticker

DATA_DIR  = Path('data')
OUT_FILE  = Path('features.csv')

print("="*60)
print(" STEP 2: Building ML Features")
print("="*60)

def compute_rsi(series):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_features(df, ticker):
    """Build features for every trading day. No look-ahead."""
    df = df.copy()
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    # ── Price features ──────────────────────────────────────────
    df['ret_1d']  = df['Close'].pct_change(1)
    df['ret_3d']  = df['Close'].pct_change(3)
    df['ret_5d']  = df['Close'].pct_change(5)
    df['ret_10d'] = df['Close'].pct_change(10)
    df['ret_20d'] = df['Close'].pct_change(20)
    df['ret_60d'] = df['Close'].pct_change(60)

    # Moving averages
    df['ma5']   = df['Close'].rolling(5).mean()
    df['ma10']  = df['Close'].rolling(10).mean()
    df['ma20']  = df['Close'].rolling(20).mean()
    df['ma50']  = df['Close'].rolling(50).mean()
    df['ma200'] = df['Close'].rolling(200).mean()

    # Price vs MA
    df['price_vs_ma5']  = (df['Close'] - df['ma5'])  / df['ma5']
    df['price_vs_ma20'] = (df['Close'] - df['ma20']) / df['ma20']
    df['price_vs_ma50'] = (df['Close'] - df['ma50']) / df['ma50']

    # MA crossovers
    df['ma5_vs_ma20']  = (df['ma5']  - df['ma20']) / df['ma20']
    df['ma10_vs_ma50'] = (df['ma10'] - df['ma50']) / df['ma50']

    # Momentum acceleration
    df['momentum_acceleration'] = df['ret_5d'] - df['ret_10d']

    # RSI
    df['rsi14'] = compute_rsi(df['Close'])
    df['rsi_normalized'] = (df['rsi14'] - 50) / 50

    # Volatility features
    df['volatility_5d']  = df['ret_1d'].rolling(5).std()
    df['volatility_20d'] = df['ret_1d'].rolling(20).std()

    # High-Low range
    df['hl_range'] = (df['High'] - df['Low']) / df['Close']

    # Volume features
    df['vol_ma20']      = df['Volume'].rolling(20).mean()
    df['volume_ratio']  = df['Volume'] / df['vol_ma20']
    df['volume_trend']  = df['Volume'].rolling(5).mean() / df['vol_ma20']
    df['relative_volume'] = np.where(df['vol_ma20'] > 0, df['Volume'] / df['vol_ma20'], np.nan)

    up_vol = df['Volume'].where(df['Close'] > df['Close'].shift(1), 0)
    down_vol = df['Volume'].where(df['Close'] < df['Close'].shift(1), 0)
    up_vol_10 = up_vol.rolling(10).sum()
    down_vol_10 = down_vol.rolling(10).sum()
    df['updown_vol_ratio_10'] = np.where(down_vol_10 > 0, up_vol_10 / down_vol_10, np.nan)

    # Bollinger Band position
    bb_mid = df['Close'].rolling(20).mean()
    bb_std = df['Close'].rolling(20).std()
    df['bb_position'] = (df['Close'] - bb_mid) / (2 * bb_std)

    # Trend strength
    df['up_days_5']  = (df['ret_1d'] > 0).rolling(5).sum()  / 5
    df['up_days_10'] = (df['ret_1d'] > 0).rolling(10).sum() / 10

    # Gap
    df['gap'] = (df['Open'] - df['Close'].shift(1)) / df['Close'].shift(1)

    # Targets
    df['future_ret_5d'] = df['Close'].shift(-6) / df['Close'].shift(-1) - 1
    df['ret_5d_net']    = df['future_ret_5d'] - 0.003
    df['target']        = (df['future_ret_5d'] > 0.02).astype(int)

    # 52-week high / low
    df['high_52w'] = df['Close'].rolling(252, min_periods=1).max()
    df['low_52w']  = df['Close'].rolling(252, min_periods=1).min()
    df['dist_52w_high_raw'] = (df['high_52w'] - df['Close']) / (df['high_52w'] - df['low_52w']).replace(0, np.nan)
    df['dist_52w_low_raw']  = (df['Close'] - df['low_52w']) / (df['high_52w'] - df['low_52w']).replace(0, np.nan)
    df['52_week_range_position'] = (df['Close'] - df['low_52w']) / (df['high_52w'] - df['low_52w']).replace(0, np.nan)

    # Market-relative placeholders (filled after Nifty merge)
    df['stock_vs_nifty_5d']  = np.nan
    df['stock_vs_nifty_20d'] = np.nan
    df['stock_vs_nifty_60d'] = np.nan

    df['ticker'] = ticker
    return df

# Load Nifty index features
BENCHMARK_DIR = Path('benchmark')
NIFTY_INDEX_FILE = BENCHMARK_DIR / 'NIFTY50.csv'
if NIFTY_INDEX_FILE.exists():
    nifty_df = pd.read_csv(NIFTY_INDEX_FILE, index_col=0)
    nifty_df.index = pd.to_datetime(nifty_df.index)
    nifty_df = nifty_df.sort_index()
    if 'Adj Close' in nifty_df.columns:
        nifty_df['Close'] = nifty_df['Adj Close']
    nifty_df['nifty_ret_1d']  = nifty_df['Close'].pct_change(1)
    nifty_df['nifty_ret_5d']  = nifty_df['Close'].pct_change(5)
    nifty_df['nifty_ret_10d'] = nifty_df['Close'].pct_change(10)
    nifty_df['nifty_ret_20d'] = nifty_df['Close'].pct_change(20)
    nifty_df['nifty_ret_60d'] = nifty_df['Close'].pct_change(60)
    nifty_df['nifty_ma50']    = nifty_df['Close'].rolling(50).mean()
    nifty_df['nifty_ma200']   = nifty_df['Close'].rolling(200).mean()
    nifty_df['nifty_above_ma50'] = (nifty_df['Close'] > nifty_df['nifty_ma50']).astype(int)
    nifty_df['nifty_price_vs_ma200'] = nifty_df['Close'] / nifty_df['nifty_ma200'] - 1
    nifty_df['nifty_ma50_vs_ma200'] = nifty_df['nifty_ma50'] / nifty_df['nifty_ma200'] - 1
    nifty_df['nifty_volatility_20d'] = nifty_df['Close'].pct_change(1).rolling(20).std()
    nifty_df['nifty_rsi14'] = compute_rsi(nifty_df['Close'])
    nifty_features = nifty_df[[
        'nifty_ret_1d','nifty_ret_5d','nifty_ret_10d','nifty_ret_20d','nifty_ret_60d',
        'nifty_above_ma50','nifty_rsi14','nifty_volatility_20d',
        'nifty_price_vs_ma200','nifty_ma50_vs_ma200'
    ]].copy()
    print('Added Nifty regime features')
else:
    nifty_features = pd.DataFrame()
    print('Nifty index file missing – market-relative features will be NaN')

print('Added RelativeVolume feature')

# Process universe
all_features = []
universe_df = load_universe(ROOT / 'universe' / 'universe.csv')
universe_tickers = [normalize_ticker(t) for t in universe_df['Ticker'].tolist() if str(t).strip()]
universe_tickers = list(dict.fromkeys(universe_tickers))

existing_files = []
missing_tickers = []
for ticker in universe_tickers:
    csv_path = DATA_DIR / f"{ticker}.csv"
    if csv_path.exists():
        existing_files.append(csv_path)
    else:
        missing_tickers.append(ticker)

print(f"Universe size         : {len(universe_tickers)}")
print(f"Existing CSV files    : {len(existing_files)}")
print(f"Missing CSV files     : {len(missing_tickers)}")
print(f"Stocks processed      : {len(existing_files)}\n")

sector_missing = []
for i, f in enumerate(sorted(existing_files)):
    ticker = f.stem
    try:
        df = pd.read_csv(f, index_col=0)
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
        # Merge Nifty
        if not nifty_features.empty:
            df_feat = df_feat.merge(nifty_features, left_index=True, right_index=True, how='left')
            df_feat['stock_vs_nifty_5d']  = df_feat['ret_5d']  - df_feat['nifty_ret_5d']
            df_feat['stock_vs_nifty_20d'] = df_feat['ret_20d'] - df_feat['nifty_ret_20d']
            df_feat['stock_vs_nifty_60d'] = df_feat['ret_60d'] - df_feat['nifty_ret_60d']
        # Sector handling
        if 'sector' in df_feat.columns:
            sector_ret = df_feat.groupby(['Date','sector'])['ret_5d'].transform('mean')
            df_feat['stock_minus_sector_ret'] = df_feat['ret_5d'] - sector_ret
            sector_nifty = df_feat.groupby(['Date','sector'])['nifty_ret_5d'].transform('mean')
            df_feat['sector_minus_nifty_ret'] = sector_nifty - df_feat['nifty_ret_5d']
            df_feat['sector_rank_pctile'] = df_feat.groupby(['Date','sector'])['ret_5d'].rank(pct=True)
        else:
            sector_missing.append(ticker)
        # Drop rows without enough data
        feature_cols = [c for c in df_feat.columns if c not in ['ticker','target','future_ret_5d','Open','High','Low','Close','Volume']]
        df_feat = df_feat.dropna(subset=feature_cols + ['target'])
        all_features.append(df_feat)
        if (i+1) % 20 == 0:
            print(f"  {i+1}/{len(existing_files)} processed")
    except Exception as e:
        print(f"  ERROR {ticker}: {e}")

print('Added updown_vol_ratio_10')

# Combine
full = pd.concat(all_features, ignore_index=False)
full = full.reset_index().rename(columns={'index':'Date'})

# Helper for safe percentile creation (ASCII messages only)
def safe_add_percentile(df, source_col, new_col):
    if source_col in df.columns:
        df[new_col] = df.groupby('Date')[source_col].rank(pct=True)
        print(f"[OK] {new_col} computed from {source_col}")
    else:
        print(f"[SKIP] {new_col} – source column '{source_col}' not found")

# Return percentiles
safe_add_percentile(full, 'ret_5d',  'ret_5d_pctile')
safe_add_percentile(full, 'ret_20d', 'ret_20d_pctile')
safe_add_percentile(full, 'ret_60d', 'ret_60d_pctile')
# Relative strength / volume / volatility
safe_add_percentile(full, 'rs_ret_60d', 'rel_strength_pctile')
safe_add_percentile(full, 'relative_volume', 'rel_volume_pctile')
safe_add_percentile(full, 'volatility_20d', 'rel_volatility_pctile')
# 52-week distance percentiles
safe_add_percentile(full, 'dist_52w_high_raw', 'dist_52w_high_pctile')
safe_add_percentile(full, 'dist_52w_low_raw',  'dist_52w_low_pctile')

# Market-breadth daily features
ma20_mask = full['Close'] > full['ma20']
ma50_mask = full['Close'] > full['ma50']
breadth = full.groupby('Date').apply(lambda d: pd.Series({
    'pct_above_20dma': ma20_mask.loc[d.index].mean(),
    'pct_above_50dma': ma50_mask.loc[d.index].mean(),
    'adv_decl_ratio': ((d['Close'] > d['Open']).sum()) / max((d['Close'] < d['Open']).sum(), 1)
}))
full = full.merge(breadth, left_on='Date', right_index=True, how='left')
full['new_52w_high'] = (full['Close'] == full['high_52w']).astype(int)
full['new_52w_low']  = (full['Close'] == full['low_52w']).astype(int)

# Cross-sectional momentum rank (cs_rank_20d)
print("\nAdding cross-sectional momentum rank (cs_rank_20d)...")
cs_rank_list = []
for date in full['Date'].unique():
    date_data = full[full['Date'] == date].copy()
    valid = date_data.dropna(subset=['ret_20d'])
    if len(valid) > 1:
        ranks = valid['ret_20d'].rank(method='average')
        percentile = (ranks - 1) / (len(ranks) - 1)
        cs_rank_list.append(pd.DataFrame({
            'Date': date,
            'ticker': valid['ticker'].values,
            'cs_rank_20d': percentile.values
        }))
    elif len(valid) == 1:
        cs_rank_list.append(pd.DataFrame({
            'Date': [date],
            'ticker': valid['ticker'].values,
            'cs_rank_20d': [0.5]
        }))
if cs_rank_list:
    cs_rank_df = pd.concat(cs_rank_list, ignore_index=True)
    full = full.merge(cs_rank_df, on=['Date','ticker'], how='left')

# Correlation report for newly added features
new_features = [
    'ret_5d_pctile','ret_20d_pctile','ret_60d_pctile',
    'rel_strength_pctile','rel_volume_pctile','rel_volatility_pctile',
    'dist_52w_high_raw','dist_52w_low_raw','dist_52w_high_pctile','dist_52w_low_pctile',
    '52_week_range_position','pct_above_20dma','pct_above_50dma','adv_decl_ratio',
    'new_52w_high','new_52w_low','stock_vs_nifty_5d','stock_vs_nifty_20d','stock_vs_nifty_60d',
    'stock_minus_sector_ret','sector_minus_nifty_ret','sector_rank_pctile'
]
if sector_missing:
    new_features = [f for f in new_features if f not in ['stock_minus_sector_ret','sector_minus_nifty_ret','sector_rank_pctile']]

# Numeric-only correlation: exclude identifier/target columns
numeric_cols = full.select_dtypes(include='number').columns
exclude_id = ['ticker','Date','target','future_ret_5d','ret_5d_net']
numeric_existing = full[numeric_cols].drop(columns=[c for c in exclude_id if c in numeric_cols])

corr_report_lines = []
for feat in new_features:
    if feat not in numeric_existing.columns:
        continue
    for other in numeric_existing.columns:
        if other == feat:
            continue
        corr = numeric_existing[feat].corr(numeric_existing[other])
        if pd.notnull(corr) and abs(corr) > 0.98:
            corr_report_lines.append(f"{feat} highly correlated with {other}: {corr:.3f}")

if corr_report_lines:
    with open('correlation_report.txt', 'w') as f:
        f.write('\n'.join(corr_report_lines))
    print(f"Correlation report written with {len(corr_report_lines)} high-corr entries")
else:
    print("No highly correlated existing features.")

# Sector missing warning
if sector_missing:
    with open('sector_missing_report.md','w') as f:
        f.write('# Sector Mapping Missing Warning\n\n')
        f.write('The following tickers lack a `sector` column, so sector-based features were skipped:\n\n')
        for t in sector_missing:
            f.write(f"- {t}\n")
        f.write('\nYou can obtain sector mapping from a reliable source (e.g., NSE sector list) and add a `sector` column to the corresponding CSV files.\n')
    print(f"Sector missing warning written for {len(sector_missing)} tickers")

# Save final feature set
full.to_csv(OUT_FILE, index=False)

feature_cols = [c for c in full.columns if c not in ['Date','ticker','target','future_ret_5d','Open','High','Low','Close','Volume']]

print("\n"+"="*60)
print(" DONE")
print("="*60)
print(f" Total rows          : {len(full):,}")
print(f" Features per stock  : {len(feature_cols)}")
print(f" Date range          : {str(full['Date'].min())[:10]} -> {str(full['Date'].max())[:10]}")
print(f" Target distribution : {full['target'].value_counts().to_dict()}")
print("\n Target = 1 means stock will rise 2%+ in next 5 days")
print(f" Stocks processed    : {full['ticker'].nunique()}")
print(f" Base rate           : {full['target'].mean()*100:.1f}% of days qualify")
print("\n Saved -> features.csv")
print(" Next: Run step3_train_model.py")
print("="*60)
