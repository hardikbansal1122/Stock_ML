#!/usr/bin/env python3
"""
STEP 1: Download 3 years of historical data for Nifty 200 stocks.
Run this once. Takes ~10-15 minutes.
"""

import yfinance as yf
import pandas as pd
import time
from pathlib import Path

OUTPUT = Path('data')
OUTPUT.mkdir(exist_ok=True)

# ── Nifty 200 stocks (NSE ticker symbols) ────────────────────────────────
# These are the 200 most liquid stocks on NSE
NIFTY_200 = [
    # Nifty 50 (large cap)
    "RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK","HINDUNILVR","ITC",
    "SBIN","BHARTIARTL","KOTAKBANK","LT","AXISBANK","ASIANPAINT","MARUTI",
    "SUNPHARMA","TITAN","ULTRACEMCO","BAJFINANCE","WIPRO","HCLTECH",
    "NESTLEIND","TECHM","POWERGRID","NTPC","TATAMOTORS","ONGC","JSWSTEEL",
    "ADANIENT","ADANIPORTS","BAJAJFINSV","COALINDIA","DIVISLAB","DRREDDY",
    "EICHERMOT","GRASIM","HDFCLIFE","HEROMOTOCO","HINDALCO","INDUSINDBK",
    "CIPLA","BPCL","BRITANNIA","APOLLOHOSP","TATACONSUM","SBILIFE",
    "UPL","TATASTEEL","M&M","BAJAJ-AUTO","SHREECEM",
    # Nifty Next 50
    "SIEMENS","HAL","ADANIGREEN","PIDILITIND","MCDOWELL-N","HAVELLS",
    "DABUR","BERGEPAINT","MARICO","GODREJCP","COLPAL","TORNTPHARM",
    "AMBUJACEM","ACC","BANKBARODA","CANBK","PNBHOUSING","FEDERALBNK",
    "IDFCFIRSTB","AUBANK","BANDHANBNK","MUTHOOTFIN","CHOLAFIN","LICHSGFIN",
    "RECLTD","PFC","IRFC","NHPC","SJVN","CESC","TATAPOWER","ADANIPOWER",
    "ADANITRANS","TORNTPOWER","ZOMATO","NYKAA","PAYTM","POLICYBZR",
    "DELHIVERY","CARTRADE","EASEMYTRIP","IRCTC","RAILVIKAS","RVNL",
    "GMRINFRA","HUDCO","NBCC","PRAJIND","SUZLON","RPOWER",
    # Nifty Midcap 100
    "AUROPHARMA","ALKEM","BIOCON","GLAND","LALPATHLAB","METROPOLIS",
    "MAXHEALTH","FORTIS","NARAYANA","KIMS","YATHARTH","RAINBOW",
    "JUBLFOOD","DEVYANI","SAPPHIRE","WESTLIFE","BARBEQUE","SPECIALITY",
    "TRENT","VSTIND","VEDL","NATIONALUM","HINDZINC","HINDCOPPER",
    "MOIL","GMDC","NMDC","KIOCL","IOLCP","DEEPAKNTR",
    "GNFC","GSFC","COROMANDEL","CHAMBALFERT","FACT","NFL",
    "TATACHEM","VINDHYATEL","GALAXYSURF","NOCIL","ROSSARI","NEOGEN",
    "AAVAS","CANFINHOME","APTUS","HOMEFIRST","REPCO","IBULHSGFIN",
    "SUNTV","ZEEL","PVRINOX","INOXWIND","NETWORK18","TV18BRDCST",
    "MPHASIS","LTTS","COFORGE","PERSISTENT","CYIENT","KPITTECH",
    "TATAELXSI","SONACOMS","BHEL","BEL","BEML","MIDHANI",
    "COCHINSHIP","MAZAGON","GRSE","GARFIBRES","TEXRAIL","TIINDIA",
    "SCHAEFFLER","TIMKEN","SKF","GRINDWELL","CARBORUNIV","WENDT",
    "PIDILITIND","ASTRAL","SUPREMEIND","FINOLEX","PRINCEPIPE","VGUARD",
    # Additional liquid stocks
    "PAGEIND","WHIRLPOOL","VOLTAS","BLUESTAR","CROMPTON","ORIENTELEC",
    "SYMPHONY","AMBER","DIXON","KAYNES","SYRMA","AVALON",
    "DMART","TATACOMM","INDIAMART","JUSTDIAL","NAUKRI","MAKEMYTRIP",
    "POLICYBZR","CENSUSINDIA","ANGELONE","CDSL","BSE","MCX",
    "MANAPPURAM","UGROCAP","CREDITACC","SPANDANA","ARMANFIN","FUSION",
]

# Remove duplicates and limit to 200
NIFTY_200 = list(dict.fromkeys(NIFTY_200))[:200]

print(f"="*60)
print(f" STEP 1: Downloading {len(NIFTY_200)} NSE stocks")
print(f"="*60)
print(f"\nThis will take 10-15 minutes. Go grab chai ☕\n")

# ── Download data ────────────────────────────────────────────────────────
failed = []
success = 0

for i, ticker in enumerate(NIFTY_200):
    nse_ticker = f"{ticker}.NS"
    out_file   = OUTPUT / f"{ticker}.csv"

    if out_file.exists():
        print(f"  [{i+1:3}/{len(NIFTY_200)}] {ticker:<20} SKIP (already downloaded)")
        success += 1
        continue

    try:
        df = yf.download(
            nse_ticker,
            start="2021-01-01",
            end=None,          # today
            progress=False,
            auto_adjust=True
        )

        if len(df) < 100:
            print(f"  [{i+1:3}/{len(NIFTY_200)}] {ticker:<20} SKIP (only {len(df)} rows)")
            failed.append(ticker)
            continue

        # Flatten multi-index columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.to_csv(out_file)
        print(f"  [{i+1:3}/{len(NIFTY_200)}] {ticker:<20} ✓ ({len(df)} rows)")
        success += 1

    except Exception as e:
        print(f"  [{i+1:3}/{len(NIFTY_200)}] {ticker:<20} FAILED: {str(e)[:40]}")
        failed.append(ticker)

    # Small delay to avoid rate limiting
    if (i+1) % 20 == 0:
        time.sleep(2)

print(f"\n{'='*60}")
print(f" DONE: {success} stocks downloaded, {len(failed)} failed")
if failed:
    print(f" Failed: {', '.join(failed[:10])}")
print(f" Data saved to: ./data/")
print(f"\n Next: Run step2_build_features.py")
print(f"{'='*60}")
