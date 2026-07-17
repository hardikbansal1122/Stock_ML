#!/usr/bin/env python3
"""
STEP 5: Daily Live Scanner
Run this every morning before 9:15 AM IST.
It downloads yesterday's data, runs the model,
and tells you which stocks to buy today.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone, date
import warnings
import yfinance as yf
import pandas as pd
import numpy as np
import pickle

warnings.filterwarnings('ignore')

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from universe import get_universe_tickers, normalize_ticker

DATA_DIR = Path('data')

print("="*65)
print(f" DAILY SCANNER — {datetime.now().strftime('%d %B %Y, %I:%M %p')}")
print("="*65)

# ── Load saved model ──────────────────────────────────────────────────────
try:
    with open('xgb_model.pkl','rb') as f: model = pickle.load(f)
    with open('scaler.pkl','rb') as f: scaler = pickle.load(f)
    features_df = pd.read_csv('feature_list.csv')
    FEATURE_COLS = features_df['feature'].tolist()
    print("\n✅ Model loaded")
except FileNotFoundError:
    print("❌ Model not found. Run step3_train_model.py first.")
    exit()

# ── Load universe from the shared CSV ─────────────────────────────────────
NIFTY_200 = [normalize_ticker(t) for t in get_universe_tickers(ROOT / 'universe' / 'universe.csv')]
NIFTY_200 = list(dict.fromkeys(NIFTY_200))

IST = timezone(timedelta(hours=5, minutes=30))

NSE_HOLIDAYS = {
    date(2024, 1, 1): "New Year's Day",
    date(2024, 1, 26): "Republic Day",
    date(2024, 3, 25): "Holi",
    date(2024, 3, 29): "Good Friday",
    date(2024, 4, 14): "Dr. Babasaheb Ambedkar Jayanti",
    date(2024, 4, 21): "Mahavir Jayanti",
    date(2024, 8, 15): "Independence Day",
    date(2024, 9, 7): "Ganesh Chaturthi",
    date(2024, 10, 2): "Gandhi Jayanti",
    date(2024, 11, 1): "Diwali",
    date(2024, 11, 15): "Guru Nanak Jayanti",
    date(2024, 12, 25): "Christmas Day",
    date(2025, 1, 1): "New Year's Day",
    date(2025, 1, 26): "Republic Day",
    date(2025, 3, 14): "Holi",
    date(2025, 4, 18): "Good Friday",
    date(2025, 4, 14): "Dr. Babasaheb Ambedkar Jayanti",
    date(2025, 4, 12): "Mahavir Jayanti",
    date(2025, 8, 15): "Independence Day",
    date(2025, 9, 26): "Ganesh Chaturthi",
    date(2025, 10, 2): "Gandhi Jayanti",
    date(2025, 11, 1): "Diwali",
    date(2025, 11, 5): "Guru Nanak Jayanti",
    date(2025, 12, 25): "Christmas Day",
    date(2026, 1, 1): "New Year's Day",
    date(2026, 1, 26): "Republic Day",
    date(2026, 3, 2): "Holi",
    date(2026, 4, 3): "Good Friday",
    date(2026, 4, 1): "Mahavir Jayanti",
    date(2026, 4, 14): "Dr. Babasaheb Ambedkar Jayanti",
    date(2026, 8, 15): "Independence Day",
    date(2026, 9, 16): "Ganesh Chaturthi",
    date(2026, 10, 2): "Gandhi Jayanti",
    date(2026, 11, 14): "Diwali",
    date(2026, 11, 30): "Guru Nanak Jayanti",
    date(2026, 12, 25): "Christmas Day",
}

def get_today_ist():
    return datetime.now(IST).date()


def is_nse_trading_holiday(check_date):
    return check_date in NSE_HOLIDAYS


def check_market_open():
    today = get_today_ist()
    if today.weekday() == 5:
        print(f"\nNSE is closed today ({today:%A, %d %b %Y}). Reason: Saturday.")
        return False
    if today.weekday() == 6:
        print(f"\nNSE is closed today ({today:%A, %d %b %Y}). Reason: Sunday.")
        return False
    if is_nse_trading_holiday(today):
        holiday = NSE_HOLIDAYS[today]
        print(f"\nNSE is closed today ({today:%A, %d %b %Y}). Reason: {holiday}.")
        return False
    return True

# ── Feature engineering function ─────────────────────────────────────────
def compute_features_single(df):
    df = df.copy()
    df['ret_1d']  = df['Close'].pct_change(1)
    df['ret_3d']  = df['Close'].pct_change(3)
    df['ret_5d']  = df['Close'].pct_change(5)
    df['ret_10d'] = df['Close'].pct_change(10)
    df['ret_20d'] = df['Close'].pct_change(20)
    df['ma5']  = df['Close'].rolling(5).mean()
    df['ma10'] = df['Close'].rolling(10).mean()
    df['ma20'] = df['Close'].rolling(20).mean()
    df['ma50'] = df['Close'].rolling(50).mean()
    df['price_vs_ma5']  = (df['Close']-df['ma5'])/df['ma5']
    df['price_vs_ma20'] = (df['Close']-df['ma20'])/df['ma20']
    df['price_vs_ma50'] = (df['Close']-df['ma50'])/df['ma50']
    df['ma5_vs_ma20']   = (df['ma5']-df['ma20'])/df['ma20']
    df['ma10_vs_ma50']  = (df['ma10']-df['ma50'])/df['ma50']
    delta = df['Close'].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, np.nan)
    df['rsi14']          = 100-(100/(1+rs))
    df['rsi_normalized'] = (df['rsi14']-50)/50
    df['volatility_5d']  = df['ret_1d'].rolling(5).std()
    df['volatility_20d'] = df['ret_1d'].rolling(20).std()
    df['hl_range']       = (df['High']-df['Low'])/df['Close']
    df['vol_ma20']       = df['Volume'].rolling(20).mean()
    df['volume_ratio']   = df['Volume']/df['vol_ma20']
    df['volume_trend']   = df['Volume'].rolling(5).mean()/df['vol_ma20']
    bb_mid = df['Close'].rolling(20).mean()
    bb_std = df['Close'].rolling(20).std()
    df['bb_position']    = (df['Close']-bb_mid)/(2*bb_std)
    df['up_days_5']      = (df['ret_1d']>0).rolling(5).sum()/5
    df['up_days_10']     = (df['ret_1d']>0).rolling(10).sum()/10
    df['gap']            = (df['Open']-df['Close'].shift(1))/df['Close'].shift(1)
    return df

# ── Scan all stocks ───────────────────────────────────────────────────────
if not check_market_open():
    print("\nNo signals generated because NSE is closed today.")
    exit()

print(f"\nScanning {len(NIFTY_200)} stocks...\n")

signals = []

for ticker in NIFTY_200:
    try:
        # Try NSE first, then BSE
        if ticker.endswith('.BO'):
            nse_ticker = ticker
        else:
            nse_ticker = f"{ticker}.NS"
            
        df = yf.download(nse_ticker, period="6mo", progress=False, auto_adjust=True)
        
        # If NSE failed, try BSE
        if len(df) < 10 and not ticker.endswith('.BO'):
            df = yf.download(f"{ticker}.BO", period="6mo", progress=False, auto_adjust=True)

        if len(df) < 60:
            continue

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df[['Open','High','Low','Close','Volume']].dropna()
        df = compute_features_single(df)

        # Get latest row (today's signal)
        latest = df.iloc[-1]
        feat_values = latest[FEATURE_COLS].values.reshape(1, -1)

        # Check for NaN
        if np.isnan(feat_values).any():
            continue

        # Predict
        confidence = model.predict_proba(feat_values)[0][1]

        if confidence >= 0.60:
            signals.append({
                'Ticker':      ticker,
                'Confidence':  confidence,
                'Close':       latest['Close'],
                'RSI':         latest['rsi14'],
                'Volume_Ratio':latest['volume_ratio'],
                'MA20_Signal': latest['price_vs_ma20'],
                'Momentum_5d': latest['ret_5d'] * 100,
            })

    except Exception as e:
        pass

# ── Display results ───────────────────────────────────────────────────────
signals_df = pd.DataFrame(signals)
if len(signals_df) > 0:
    signals_df = signals_df.sort_values('Confidence', ascending=False)

print(f"\n{'='*65}")
print(f" TODAY'S SIGNALS — {datetime.now().strftime('%d %b %Y')}")
print(f"{'='*65}")

if len(signals_df) == 0:
    print("\n No high-confidence signals today.")
    print(" Wait for tomorrow or lower the threshold slightly.")
else:
    print(f"\n {len(signals_df)} stocks flagged (≥60% confidence)\n")
    print(f" {'Rank':>4} {'Ticker':>12} {'Conf%':>7} {'Price':>9} {'RSI':>6} {'Vol Ratio':>10} {'5d Ret%':>8}")
    print(f" {'-'*60}")

    for rank, (_, r) in enumerate(signals_df.iterrows(), 1):
        conf_bar = '▓' * int(r['Confidence']*10)
        print(f" {rank:>4}. {r['Ticker']:>11} {r['Confidence']*100:>6.1f}% "
              f"₹{r['Close']:>8,.0f} {r['RSI']:>5.0f} {r['Volume_Ratio']:>9.1f}x "
              f"{r['Momentum_5d']:>+7.1f}%")

    # Top 5 recommendations
    top5 = signals_df.head(5)
    print(f"\n{'─'*65}")
    print(f" TOP 5 BUYS FOR TODAY")
    print(f"{'─'*65}")
    for rank, (_, r) in enumerate(top5.iterrows(), 1):
        rsi_note  = "Oversold 🟢" if r['RSI']<40 else "Neutral ⚪" if r['RSI']<60 else "Overbought 🔴"
        vol_note  = "Volume spike 🔥" if r['Volume_Ratio']>1.5 else "Normal volume"
        print(f"\n {rank}. {r['Ticker']}")
        print(f"    Model confidence : {r['Confidence']*100:.1f}%")
        print(f"    Current price    : ₹{r['Close']:,.0f}")
        print(f"    RSI (14)         : {r['RSI']:.0f} — {rsi_note}")
        print(f"    Volume           : {r['Volume_Ratio']:.1f}x average — {vol_note}")
        print(f"    5-day momentum   : {r['Momentum_5d']:+.1f}%")
        print(f"    Strategy         : Buy today, sell in 5 trading days")
        print(f"    Stop loss        : -3% from entry price (risk management)")

# ── Risk management reminder ──────────────────────────────────────────────
print(f"""
{'─'*65}
 RISK MANAGEMENT RULES (never skip these)
{'─'*65}
 1. Never put more than 10% of capital in one stock
 2. Always set stop-loss at -3% from your buy price
 3. Sell after 5 trading days regardless of profit/loss
 4. If you have 3 losses in a row → stop for the week
 5. Start with ₹10,000-20,000 until you validate the system
 6. This model is a tool, not a guarantee. Your risk, your money.
{'─'*65}
""")

# Save today's signals
signals_df.to_csv(f"signals_{datetime.now().strftime('%Y%m%d')}.csv", index=False)
print(f" Signals saved → signals_{datetime.now().strftime('%Y%m%d')}.csv")
