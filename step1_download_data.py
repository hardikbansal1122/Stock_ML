#!/usr/bin/env python3
"""
STEP 1: Download 3 years of historical data for Nifty 200 stocks.
Run this once. Takes ~10-15 minutes.
"""

import argparse
import os
import sys
import tempfile
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from universe import get_universe_path, get_universe_tickers, normalize_ticker

OUTPUT = Path('data')
OUTPUT.mkdir(exist_ok=True)


def load_universe(path=None):
    return pd.DataFrame({'Ticker': get_universe_tickers(path)})


def build_download_plan(universe_df, force=False):
    plan = []
    for _, row in universe_df.iterrows():
        ticker = normalize_ticker(row['Ticker'])
        if not ticker:
            continue
        out_file = OUTPUT / f"{ticker}.csv"
        plan.append({
            'Ticker': ticker,
            'OutputFile': out_file,
            'Skip': False,
        })
    return plan


def normalize_price_frame(df):
    if df is None:
        return pd.DataFrame(columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])

    df = df.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    if 'Date' not in df.columns:
        if df.index.name is not None and str(df.index.name).lower() == 'date':
            df = df.reset_index()
        else:
            df = df.reset_index().rename(columns={'index': 'Date'})

    df['Date'] = pd.to_datetime(df['Date'])

    if 'Close' not in df.columns and 'Adj Close' in df.columns:
        df['Close'] = df['Adj Close']

    required_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
    for col in required_columns:
        if col not in df.columns:
            df[col] = pd.NA

    df = df.loc[:, required_columns].copy()
    df = df.sort_values('Date').drop_duplicates(subset=['Date']).reset_index(drop=True)
    return df


def save_price_frame(df, out_file):
    temp_handle = None
    try:
        with tempfile.NamedTemporaryFile('w', delete=False, dir=str(out_file.parent), suffix='.tmp') as temp_handle:
            temp_path = temp_handle.name
        df.to_csv(temp_path, index=False)
        os.replace(temp_path, out_file)
        return True
    except Exception:
        if temp_handle is not None and os.path.exists(temp_handle.name):
            os.remove(temp_handle.name)
        return False


def download_ticker(ticker, out_file, force=False):
    nse_ticker = f"{ticker}.NS"
    try:
        if out_file.exists() and not force:
            existing_df = normalize_price_frame(pd.read_csv(out_file, parse_dates=['Date']))
            if existing_df.empty or 'Date' not in existing_df.columns:
                return {
                    'Ticker': ticker,
                    'Status': 'Failed',
                    'Rows': 0,
                    'EarliestDate': None,
                    'LatestDate': None,
                    'MissingValues': None,
                    'ErrorMessage': 'Existing file is invalid',
                }

            latest_date = existing_df['Date'].max().normalize()
            today = pd.Timestamp.today().normalize()
            if latest_date >= today:
                return {
                    'Ticker': ticker,
                    'Status': 'UpToDate',
                    'Rows': len(existing_df),
                    'EarliestDate': existing_df['Date'].min().date().isoformat(),
                    'LatestDate': existing_df['Date'].max().date().isoformat(),
                    'MissingValues': int(existing_df.isna().sum().sum()),
                    'ErrorMessage': 'Already up to date',
                }

            start_date = (latest_date + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
            new_df = yf.download(
                nse_ticker,
                start=start_date,
                end=None,
                progress=False,
                auto_adjust=True,
            )
            new_df = normalize_price_frame(new_df)

            if new_df.empty:
                return {
                    'Ticker': ticker,
                    'Status': 'UpToDate',
                    'Rows': len(existing_df),
                    'EarliestDate': existing_df['Date'].min().date().isoformat(),
                    'LatestDate': existing_df['Date'].max().date().isoformat(),
                    'MissingValues': int(existing_df.isna().sum().sum()),
                    'ErrorMessage': 'Already up to date',
                }

            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            combined_df = normalize_price_frame(combined_df)
            if not save_price_frame(combined_df, out_file):
                return {
                    'Ticker': ticker,
                    'Status': 'Failed',
                    'Rows': len(existing_df),
                    'EarliestDate': existing_df['Date'].min().date().isoformat(),
                    'LatestDate': existing_df['Date'].max().date().isoformat(),
                    'MissingValues': int(existing_df.isna().sum().sum()),
                    'ErrorMessage': 'Failed to save updated file',
                }

            return {
                'Ticker': ticker,
                'Status': 'Downloaded',
                'Rows': len(combined_df),
                'EarliestDate': combined_df['Date'].min().date().isoformat(),
                'LatestDate': combined_df['Date'].max().date().isoformat(),
                'MissingValues': int(combined_df.isna().sum().sum()),
                'ErrorMessage': '',
            }

        if force and out_file.exists():
            out_file.unlink(missing_ok=True)

        df = yf.download(
            nse_ticker,
            start="2021-01-01",
            end=None,
            progress=False,
            auto_adjust=True,
        )
        df = normalize_price_frame(df)

        if df.empty or len(df) < 100:
            return {
                'Ticker': ticker,
                'Status': 'Failed',
                'Rows': len(df),
                'EarliestDate': None,
                'LatestDate': None,
                'MissingValues': None,
                'ErrorMessage': 'Insufficient rows',
            }

        if not save_price_frame(df, out_file):
            return {
                'Ticker': ticker,
                'Status': 'Failed',
                'Rows': len(df),
                'EarliestDate': df['Date'].min().date().isoformat() if 'Date' in df.columns else None,
                'LatestDate': df['Date'].max().date().isoformat() if 'Date' in df.columns else None,
                'MissingValues': int(df.isna().sum().sum()),
                'ErrorMessage': 'Failed to save initial file',
            }

        return {
            'Ticker': ticker,
            'Status': 'Downloaded',
            'Rows': len(df),
            'EarliestDate': df['Date'].min().date().isoformat() if 'Date' in df.columns else None,
            'LatestDate': df['Date'].max().date().isoformat() if 'Date' in df.columns else None,
            'MissingValues': int(df.isna().sum().sum()),
            'ErrorMessage': '',
        }
    except Exception as e:
        return {
            'Ticker': ticker,
            'Status': 'Failed',
            'Rows': 0,
            'EarliestDate': None,
            'LatestDate': None,
            'MissingValues': None,
            'ErrorMessage': str(e)[:200],
        }

# ── Nifty index history (Nifty 50) ───────────────────────────────────────
INDEX_FILE = OUTPUT / 'NIFTY50.csv'
if not INDEX_FILE.exists():
    try:
        idx_df = yf.download(
            '^NSEI',
            start='2021-01-01',
            end=None,
            progress=False,
            auto_adjust=True,
        )

        if isinstance(idx_df.columns, pd.MultiIndex):
            idx_df.columns = idx_df.columns.get_level_values(0)

        if 'Adj Close' in idx_df.columns:
            idx_df['Close'] = idx_df['Adj Close']

        idx_df.to_csv(INDEX_FILE)
        print(f"  NIFTY index saved -> {INDEX_FILE.name} ({len(idx_df)} rows)")
    except Exception as e:
        print(f"  NIFTY index download failed: {str(e)[:80]}")


def main():
    parser = argparse.ArgumentParser(description='Download stock data from the configured universe.')
    parser.add_argument('--force', action='store_true', help='Redownload existing files even if they already exist.')
    parser.add_argument('--universe', default=str(get_universe_path()), help='Path to the universe CSV file.')
    args = parser.parse_args()

    universe_df = load_universe(Path(args.universe))
    ticker_list = universe_df['Ticker'].tolist()

    print(f"=" * 60)
    print(f" STEP 1: Downloading {len(ticker_list)} NSE stocks")
    if args.force:
        print(' Force mode enabled: re-downloading existing files.')
    print(f"=" * 60)
    print(f"\nThis will take 10-15 minutes. Go grab chai ☕\n")

    plan = build_download_plan(universe_df, force=args.force)
    results = []
    failed = []
    downloaded = []
    up_to_date = []

    for i, item in enumerate(plan, start=1):
        ticker = item['Ticker']
        out_file = item['OutputFile']
        print(f"  [{i:3}/{len(plan)}] {ticker:<20}", end=' ')
        result = download_ticker(ticker, out_file, force=args.force)
        results.append(result)

        if result['Status'] == 'Downloaded':
            downloaded.append(ticker)
            print(f"✓ ({result['Rows']} rows)")
        elif result['Status'] == 'UpToDate':
            up_to_date.append(ticker)
            print(f"ALREADY UP TO DATE")
        else:
            failed.append(ticker)
            print(f"FAILED: {result['ErrorMessage']}")

        if i % 20 == 0:
            time.sleep(2)

    report_df = pd.DataFrame(results)
    report_df = report_df[['Ticker', 'Status', 'Rows', 'EarliestDate', 'LatestDate', 'MissingValues', 'ErrorMessage']]
    report_path = Path('download_report.csv')
    report_df.to_csv(report_path, index=False)

    print(f"\n{'='*60}")
    print(f" DONE: Downloaded={len(downloaded)} Failed={len(failed)} UpToDate={len(up_to_date)}")
    print(f" Report saved to: {report_path}")
    print(f" Data saved to: ./data/")
    print(f"\n Next: Run step2_build_features.py")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
