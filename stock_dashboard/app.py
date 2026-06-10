#!/usr/bin/env python3
"""
app.py — Stock ML Dashboard v2
- Loads last scan on startup (no more dashes)
- Auto-resolves trades after 5 trading days
- Auto-fills exit price + return in Excel
Run: python app.py
Open: http://localhost:5000
"""

from pandas.core import resample
from pandas.core import resample
from pandas.core import resample
from pandas.core import resample
from pandas.core import resample
from pandas.core import resample
from pandas.core import resample
from pandas.core import resample
from flask import debughelpers
from flask import Flask, jsonify, send_from_directory, request

from auth_middleware import require_auth, require_admin, supabase, ADMIN_EMAILS
import yfinance as yf
import pandas as pd
import numpy as np
import pickle, os, json, subprocess, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

app = Flask(__name__, static_folder='static')

BASE_DIR       = Path(__file__).parent
MODEL_PATH     = BASE_DIR / 'xgb_model.pkl'
SCALER_PATH    = BASE_DIR / 'scaler.pkl'
FEAT_PATH      = BASE_DIR / 'feature_list.csv'
LAST_SCAN_PATH = BASE_DIR / 'last_scan.json'

# ── Load model ────────────────────────────────────────────────────────────
try:
    with open(MODEL_PATH,'rb') as f: MODEL = pickle.load(f)
    with open(SCALER_PATH,'rb') as f: SCALER = pickle.load(f)
    FEATURE_COLS = pd.read_csv(FEAT_PATH)['feature'].tolist()
    print("✅ Model loaded")
except Exception as e:
    print(f"❌ Model load failed: {e}")
    MODEL = None

NIFTY_TICKERS = list(dict.fromkeys([
    "RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK","HINDUNILVR","ITC",
    "SBIN","BHARTIARTL","KOTAKBANK","LT","AXISBANK","ASIANPAINT","MARUTI",
    "SUNPHARMA","TITAN","ULTRACEMCO","BAJFINANCE","WIPRO","HCLTECH",
    "NESTLEIND","TECHM","POWERGRID","NTPC","ONGC","JSWSTEEL",
    "ADANIENT","ADANIPORTS","BAJAJFINSV","COALINDIA","DIVISLAB","DRREDDY",
    "EICHERMOT","GRASIM","HDFCLIFE","HEROMOTOCO","HINDALCO","INDUSINDBK",
    "CIPLA","BPCL","BRITANNIA","APOLLOHOSP","TATACONSUM","SBILIFE",
    "TATASTEEL","BAJAJ-AUTO","SHREECEM","SIEMENS","HAL",
    "PIDILITIND","HAVELLS","DABUR","BERGEPAINT","MARICO","GODREJCP",
    "COLPAL","TORNTPHARM","AMBUJACEM","ACC","BANKBARODA","FEDERALBNK",
    "IDFCFIRSTB","CHOLAFIN","IRCTC","TATAPOWER","AUROPHARMA","BIOCON",
    "LALPATHLAB","JUBLFOOD","TRENT","VEDL","NATIONALUM","HINDZINC","NMDC",
    "MPHASIS","LTTS","COFORGE","PERSISTENT","KPITTECH","TATAELXSI",
    "BEL","BHEL","ASTRAL","SUPREMEIND","PAGEIND","DIXON","DMART",
    "NAUKRI","ANGELONE","CDSL","MCX","MANAPPURAM","M&M",
    "ICICIPRULI","LICI","GAIL","IOC","HINDPETRO",
    "SAIL","MOIL","WELCORP","RATNAMANI","ABCAPITAL",
    "TATACOMM","HFCL","RAILTEL","TANLA",
    "ALKEM","MANKIND","LAURUSLABS","GRANULES",
    "CONCOR","SUZLON","INOXWIND","UPL","SRF","DEEPAKNTR",
    "MUTHOOTFIN","RECLTD","PFC","IRFC","NHPC","SJVN",
    "GODREJPROP","DLF","OBEROIRLTY","PRESTIGE","BRIGADE",
    "VOLTAS","CROMPTON","BLUESTARCO","SYMPHONY",
    "BATAINDIA","ABBOTINDIA","GLAXO","PFIZER",
    "AUBANK","BANDHANBNK","POLYCAB","KEI",
    "TATACHEM","GNFC","COROMANDEL","CHAMBALFERT",
    "JKCEMENT","RAMCOCEM","PIIND","ABFRL",
]))

# ── Feature engineering ───────────────────────────────────────────────────
def compute_features(df):
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
    df['bb_position'] = (df['Close']-bb_mid)/(2*bb_std)
    df['up_days_5']   = (df['ret_1d']>0).rolling(5).sum()/5
    df['up_days_10']  = (df['ret_1d']>0).rolling(10).sum()/10
    df['gap']         = (df['Open']-df['Close'].shift(1))/df['Close'].shift(1)
    return df

def fetch_stock(ticker):
    for suffix in ['.NS','.BO']:
        try:
            df = yf.download(f"{ticker}{suffix}", period="6mo",
                             progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if len(df) > 60:
                return df[['Open','High','Low','Close','Volume']].dropna()
        except: continue
    return None

def get_current_price(ticker):
    for suffix in ['.NS','.BO']:
        try:
            df = yf.download(f"{ticker}{suffix}", period="5d",
                             progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if len(df) > 0:
                return float(df['Close'].iloc[-1])
        except: continue
    return None



def auto_resolve_trades():

    if not supabase:
        return []

    resolved = []

    try:

        open_trades = (
            supabase
            .table('trades')
            .select('*')
            .eq('status', 'OPEN')
            .execute()
        )

        for trade in open_trades.data or []:

            try:
                entry_date = datetime.fromisoformat(
                    trade['entry_date'].replace('Z', '+00:00')
                ).date()
            except:
                continue

            today = datetime.now(timezone.utc).date()

            # Same rule as before (7 calendar days)
            if (today - entry_date).days < 7:
                continue

            ticker = trade['ticker']
            entry_price = trade['entry_price']

            if not entry_price:
                continue

            exit_price = get_current_price(ticker)

            if not exit_price:
                continue

            return_pct = round(
                ((float(exit_price) - float(entry_price))
                 / float(entry_price)) * 100,
                2
            )

            (
                supabase
                .table('trades')
                .update({
                    'exit_price': round(exit_price, 2),
                    'exit_date': datetime.now(timezone.utc).isoformat(),
                    'return_pct': return_pct,
                    'status': 'CLOSED'
                })
                .eq('id', trade['id'])
                .execute()
            )

            resolved.append({
                'ticker': ticker,
                'entry': float(entry_price),
                'exit': round(exit_price, 2),
                'return': return_pct,
                'outcome': 'Win' if return_pct > 0 else 'Loss'
            })

    except Exception as e:
        print("AUTO RESOLVE ERROR:", e)

    return resolved

# ── Persistence ───────────────────────────────────────────────────────────
def save_last_scan(result):
    with open(LAST_SCAN_PATH,'w') as f: json.dump(result, f)

def load_last_scan():
    if not LAST_SCAN_PATH.exists(): return None
    try:
        with open(LAST_SCAN_PATH) as f: return json.load(f)
    except: return None

# ── Scanner ───────────────────────────────────────────────────────────────
def run_scanner(threshold=0.60):
    if MODEL is None:
        return {"error": "Model not loaded. Run step3_train_model.py first."}
    signals, processed, failed = [], 0, 0
    for ticker in NIFTY_TICKERS:
        try:
            df = fetch_stock(ticker)
            if df is None: failed += 1; continue
            df   = compute_features(df)
            last = df.iloc[-1]
            feat = last[FEATURE_COLS].values.reshape(1,-1)
            if np.isnan(feat).any(): continue
            conf = float(MODEL.predict_proba(feat)[0][1])
            processed += 1
            if conf >= threshold:
                signals.append({'ticker':ticker,'confidence':conf,
                    'close':float(last['Close']),'rsi':float(last['rsi14']),
                    'volume_ratio':float(last['volume_ratio']),
                    'momentum_5d':float(last['ret_5d']*100),
                    'price_vs_ma20':float(last['price_vs_ma20']*100)})
        except: failed += 1
    signals.sort(key=lambda x: x['confidence'], reverse=True)
    return {'signals':signals,'processed':processed,'failed':failed,
            'total':len(NIFTY_TICKERS),
            'timestamp':datetime.now().strftime("%d %b %Y, %I:%M %p"),
            'date':datetime.now().strftime("%d %b %Y"),
            'time':datetime.now().strftime("%I:%M %p")}

# ── Routes ────────────────────────────────────────────────────────────────
@app.route('/')
def index(): return send_from_directory('static', 'index.html')

@app.route('/dashboard')
def dashboard(): return send_from_directory('static', 'dashboard.html')

@app.route('/api/sync_user', methods=['POST'])
@require_auth
def api_sync_user():
    if not supabase:
        return jsonify({"status": "skipped", "reason": "Supabase not configured"})
        
    user = request.user
    uid = user.get('uid')
    email = user.get('email')
    display_name = user.get('name', '')
    photo_url = user.get('picture', '')
    
    try:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        # Upsert user data
        supabase.table('users').upsert({
            'uid': uid,
            'email': email,
            'display_name': display_name,
            'photo_url': photo_url,
            'last_login': now
        }).execute()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/scan')
@require_auth
def api_scan():
    # Parse threshold safely
    threshold = float(request.args.get('threshold', 0.60))

    # Run scanner
    result = run_scanner(threshold=threshold)

    

    # Current authenticated user
    uid = request.user.get('uid')

    # Store trades + scan history in Supabase
    if supabase and uid:
        for sig in result.get('signals', []):

            ticker = sig.get('ticker')

            # Check if an OPEN trade already exists
            dup = (
                supabase
                .table('trades')
                .select('id')
                .eq('uid', uid)
                .eq('ticker', ticker)
                .eq('status', 'OPEN')
                .execute()
            )

            # Only create a new trade if one doesn't already exist
            if not dup.data:
                trade_resp = (
                    supabase
                    .table('trades')
                    .insert({
                        'uid': uid,
                        'ticker': ticker,
                        'confidence': sig.get('confidence'),
                        'entry_price': sig.get('close'),
                        'entry_date': datetime.now(timezone.utc).isoformat(),
                        'status': 'OPEN'
                    })
                    .execute()
                )

                print(f"Inserted trade: {ticker} for {uid}")
                print("TRADE RESPONSE:", trade_resp)

            # ALWAYS store scan result
            print("INSERTING SCAN RESULT:", ticker)

            scan_resp = (
                supabase
                .table('scan_results')
                .insert({
                    'uid': uid,
                    'ticker': ticker,
                    'confidence': sig.get('confidence'),
                    'price': sig.get('close')
                })
                .execute()
            )

            print("SCAN RESULT RESPONSE:", scan_resp)

    save_last_scan(result)

    return jsonify(result)

@app.route('/api/last_scan')
@require_auth
def api_last_scan():

    uid = request.user.get('uid')

    response = (
        supabase
        .table('scan_results')
        .select('*')
        .eq('uid', uid)
        .order('scan_time', desc=True)
        .execute()
    )

    signals = []

    for row in response.data or []:
        signals.append({
            'ticker': row['ticker'],
            'confidence': float(row['confidence']),
            'close': float(row['price'])
        })

    return jsonify({
        'signals': signals,
        'processed': len(signals),
        'total': len(NIFTY_TICKERS)
    }
)
@app.route('/api/resolve')
@require_auth
def api_resolve():
    resolved = auto_resolve_trades()
    return jsonify({'resolved_count':len(resolved),'resolved':resolved})

@app.route('/api/history')
@require_auth
def api_history():

    uid = request.user.get('uid')

    response = (
        supabase
        .table('trades')
        .select('*')
        .eq('uid', uid)
        .order('entry_date', desc=True)
        .execute()
    )

    return jsonify({
        'history': response.data or []
    })



@app.route('/api/status')
@require_auth
def api_status():
    last = load_last_scan()
    user = request.user
    uid = user.get('uid')
    email = user.get('email')
    
    is_admin = False
    if email in ADMIN_EMAILS:
        is_admin = True
    elif supabase:
        try:
            res = supabase.table('users').select('role').eq('uid', uid).execute()
            if res.data and len(res.data) > 0 and res.data[0].get('role') == 'admin':
                is_admin = True
        except:
            pass
            
    return jsonify({'model_loaded':MODEL is not None,
                    'total_tickers':len(NIFTY_TICKERS),
                    'storage': 'supabase',
                    'last_scan_time':last.get('timestamp') if last else None,
                    'last_signals':len(last.get('signals',[])) if last else 0,
                    'is_admin': is_admin})

@app.route('/api/active_trades')
@require_auth
def api_active_trades():

    uid = uid = request.user.get('uid')

    if not supabase:
        return jsonify({'trades': []})

    try:
        response = (
            supabase
            .table('trades')
            .select('*')
            .eq('uid', uid)
            .eq('status', 'OPEN')
            .order('entry_date', desc=True)
            .execute()
        )

        return jsonify({
            'trades': response.data or []
        })

    except Exception as e:
        return jsonify({
            'trades': [],
            'error': str(e)
        }), 500
        

if __name__ == '__main__':
    print("="*60)
    print(" Stock ML Dashboard v2")
    print("="*60)
    print(f" Model    : {'✅ loaded' if MODEL else '❌ not found'}")
    print(f" Tickers  : {len(NIFTY_TICKERS)}")
    print(f"\n Open: http://localhost:5000")
    print("="*60)
    app.run(host='0.0.0.0', port=5000, debug=False)

