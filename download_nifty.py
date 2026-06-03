#!/usr/bin/env python3
"""Download NIFTY 50 history and save it as benchmark/NIFTY50.csv."""

import pandas as pd
import yfinance as yf
from pathlib import Path

BENCHMARK_DIR = Path('benchmark')
OUT_FILE = BENCHMARK_DIR / 'NIFTY50.csv'
SYMBOL = '^NSEI'


def format_date(d):
    return pd.to_datetime(d).strftime('%Y-%m-%d')


def load_existing(path):
    if not path.exists():
        return None
    df = pd.read_csv(path, parse_dates=['Date'])
    return df.sort_values('Date').reset_index(drop=True)


def sanitize_df(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    if 'Adj Close' in df.columns and 'Close' not in df.columns:
        df['Close'] = df['Adj Close']
    if 'Date' not in df.columns:
        df = df.reset_index().rename(columns={'index': 'Date'})
    df['Date'] = pd.to_datetime(df['Date'])
    cols = ['Date'] + [c for c in df.columns if c != 'Date']
    return df.loc[:, cols].sort_values('Date').reset_index(drop=True)


def print_diff(old_df, new_df):
    if old_df is None:
        print('No existing benchmark file found. The new data will be saved.')
        return

    print('Existing benchmark file found. Comparing old and new data...')
    print(f'  Old rows: {len(old_df):,}')
    print(f'  New rows: {len(new_df):,}')

    old_dates = set(old_df['Date'])
    new_dates = set(new_df['Date'])
    added = sorted(new_dates - old_dates)
    removed = sorted(old_dates - new_dates)

    print(f'  Dates added : {len(added):,}')
    print(f'  Dates removed : {len(removed):,}')

    if added:
        print('  First added date :', format_date(added[0]))
    if removed:
        print('  First removed date :', format_date(removed[0]))

    merged = old_df.merge(new_df, on='Date', how='inner', suffixes=('_old', '_new'))
    compared = merged.loc[:, ['Date'] + [c for c in merged.columns if c.endswith('_old') or c.endswith('_new')]]
    diffs = []
    for col in old_df.columns:
        if col == 'Date':
            continue
        old_col = f'{col}_old'
        new_col = f'{col}_new'
        if old_col not in compared.columns or new_col not in compared.columns:
            continue
        changed = compared[compared[old_col] != compared[new_col]]
        if not changed.empty:
            diffs.append((col, len(changed)))

    if not diffs:
        print('  No value changes detected in overlapping dates.')
    else:
        print('  Value changes detected in overlapping dates:')
        for col, count in diffs:
            print(f'    {col}: {count:,} rows changed')

        sample = []
        for col, _ in diffs[:3]:
            old_col = f'{col}_old'
            new_col = f'{col}_new'
            changed = compared[compared[old_col] != compared[new_col]].head(5)
            for _, row in changed.iterrows():
                sample.append((format_date(row['Date']), col, row[old_col], row[new_col]))

        if sample:
            print('\n  Sample differences:')
            for date, col, old_val, new_val in sample:
                print(f'    {date} | {col} | old={old_val} | new={new_val}')


def main():
    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)

    print(f'Downloading {SYMBOL} history via yfinance from 2000-01-01...')
    df = yf.download(
        SYMBOL,
        start='2000-01-01',
        progress=False,
        auto_adjust=True,
    )
    df = sanitize_df(df)

    if df.empty:
        print('ERROR: No data downloaded.')
        return

    print('\nDownloaded data summary:')
    print(f'  Rows downloaded : {len(df):,}')
    print(f'  Start date      : {format_date(df["Date"].iloc[0])}')
    print(f'  End date        : {format_date(df["Date"].iloc[-1])}')

    existing = load_existing(OUT_FILE)
    print('\nDiff before saving:')
    print_diff(existing, df)

    df.to_csv(OUT_FILE, index=False)
    print(f'\nSaved benchmark file to: {OUT_FILE}')


if __name__ == '__main__':
    main()
