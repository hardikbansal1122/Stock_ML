#!/usr/bin/env python3
"""
app.py — Stock ML Dashboard v2
- Loads last scan on startup (no more dashes)
- Auto-resolves trades after 5 trading days
- Auto-fills exit price + return in Excel
Run: python app.py
Open: http://localhost:5000
"""

from flask import Flask, jsonify, send_from_directory, request

from auth_middleware import require_auth, require_admin, supabase, ADMIN_EMAILS
import yfinance as yf
import pandas as pd
import numpy as np
import pickle, os, json, subprocess, sys
from datetime import datetime, timedelta
from pathlib import Path
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, PatternFill, Alignment
import warnings
warnings.filterwarnings('ignore')

app = Flask(__name__, static_folder='static')

BASE_DIR       = Path(__file__).parent
MODEL_PATH     = BASE_DIR / 'xgb_model.pkl'
SCALER_PATH    = BASE_DIR / 'scaler.pkl'
FEAT_PATH      = BASE_DIR / 'feature_list.csv'
EXCEL_PATH     = BASE_DIR / 'paper_trading_log.xlsx'
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

# ── Excel helpers ─────────────────────────────────────────────────────────
def init_excel():
    if EXCEL_PATH.exists(): return
    wb = Workbook()
    ws1 = wb.active
    ws1.title = "Signals Log"
    headers = ["Scan Date","Time","Ticker","Confidence%","Entry Price",
               "RSI","Vol Ratio","5d Momentum%","Target Exit Date",
               "Exit Price","Return%","Outcome","Notes"]
    for col, h in enumerate(headers, 1):
        c = ws1.cell(row=1, column=col, value=h)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1A1A1A")
        c.alignment = Alignment(horizontal="center")
    for i, w in enumerate([12,10,12,13,13,8,10,14,16,13,10,10,30], 1):
        ws1.column_dimensions[chr(64+i)].width = w

    ws2 = wb.create_sheet("Daily Summary")
    for col, h in enumerate(["Date","Signals","Avg Conf%","Top Pick","Top Conf%"], 1):
        c = ws2.cell(row=1, column=col, value=h)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1A1A1A")
        c.alignment = Alignment(horizontal="center")

    ws3 = wb.create_sheet("Performance")
    for col, h in enumerate(["Metric","Value"], 1):
        c = ws3.cell(row=1, column=col, value=h)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1A1A1A")
    for i, m in enumerate(["Total Signals","Resolved","Wins","Losses",
                            "Win Rate%","Avg Return%","Best%","Worst%"], 2):
        ws3.cell(row=i, column=1, value=m).font = Font(bold=True)
        ws3.cell(row=i, column=2, value="—")
    wb.save(EXCEL_PATH)

def log_signals_to_excel(signals):
    init_excel()
    wb   = load_workbook(EXCEL_PATH)
    ws   = wb["Signals Log"]
    now  = datetime.now()
    exit_date = (now + timedelta(days=7)).strftime("%Y-%m-%d")
    row  = ws.max_row + 1
    for s in signals:
        conf = round(s['confidence']*100, 1)
        data = [now.strftime("%Y-%m-%d"), now.strftime("%H:%M"),
                s['ticker'], conf, round(s['close'],2),
                round(s['rsi'],0), round(s['volume_ratio'],2),
                round(s['momentum_5d'],2), exit_date,
                "", "", "Pending", ""]
        for col, val in enumerate(data, 1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.alignment = Alignment(horizontal="center")
            if col == 4:
                color = "22C55E" if conf>=70 else "84CC16" if conf>=65 else "EAB308"
                cell.fill = PatternFill("solid", fgColor=color)
                cell.font = Font(bold=True, color="FFFFFF")
        row += 1

    ws2 = wb["Daily Summary"]
    nr  = ws2.max_row + 1
    if signals:
        avg = sum(s['confidence'] for s in signals)/len(signals)*100
        top = max(signals, key=lambda x: x['confidence'])
        r2  = [now.strftime("%Y-%m-%d"), len(signals), round(avg,1),
               top['ticker'], round(top['confidence']*100,1)]
    else:
        r2 = [now.strftime("%Y-%m-%d"), 0, 0, "None", 0]
    for col, val in enumerate(r2, 1):
        ws2.cell(row=nr, column=col, value=val).alignment = Alignment(horizontal="center")
    wb.save(EXCEL_PATH)

def auto_resolve_trades():
    """Auto-fill exit price + return for trades that are 7+ calendar days old."""
    if not EXCEL_PATH.exists(): return []
    init_excel()
    wb   = load_workbook(EXCEL_PATH)
    ws   = wb["Signals Log"]
    today = datetime.now().date()
    resolved = []

    for row in range(2, ws.max_row + 1):
        if ws.cell(row=row, column=12).value != "Pending": continue
        try:
            scan_date = datetime.strptime(
                str(ws.cell(row=row, column=1).value)[:10], "%Y-%m-%d").date()
        except: continue

        if (today - scan_date).days < 7: continue

        ticker      = str(ws.cell(row=row, column=3).value)
        entry_price = ws.cell(row=row, column=5).value
        if not entry_price: continue

        exit_price = get_current_price(ticker)
        if not exit_price: continue

        net_ret = round((exit_price - float(entry_price)) / float(entry_price) * 100, 2)
        outcome = "Win ✅" if net_ret > 0 else "Loss ❌"

        ws.cell(row=row, column=10).value = round(exit_price, 2)
        ws.cell(row=row, column=11).value = net_ret
        out = ws.cell(row=row, column=12)
        out.value = outcome
        out.fill  = PatternFill("solid", fgColor="22C55E" if net_ret>0 else "EF4444")
        out.font  = Font(bold=True, color="FFFFFF")
        resolved.append({'ticker':ticker,'entry':float(entry_price),
                         'exit':exit_price,'return':net_ret,'outcome':outcome})

    if resolved:
        # Update performance sheet
        ws3 = wb["Performance"]
        returns, wins, losses = [], 0, 0
        for row in range(2, ws.max_row+1):
            outcome = str(ws.cell(row=row, column=12).value)
            ret_val = ws.cell(row=row, column=11).value
            if "Win" in outcome and ret_val:
                wins += 1; returns.append(float(ret_val))
            elif "Loss" in outcome and ret_val:
                losses += 1; returns.append(float(ret_val))
        total = wins+losses
        vals  = [ws.max_row-1, total, wins, losses,
                 round(wins/total*100,1) if total else 0,
                 round(sum(returns)/len(returns),2) if returns else 0,
                 round(max(returns),2) if returns else 0,
                 round(min(returns),2) if returns else 0]
        for i, v in enumerate(vals, 2):
            ws3.cell(row=i, column=2, value=v)
        wb.save(EXCEL_PATH)
    elif ws.max_row > 1:
        wb.save(EXCEL_PATH)

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
@require_admin
def api_scan():
    threshold = float(request.args.get('threshold', 0.60))
    result = run_scanner(threshold=threshold)
    if 'signals' in result and result['signals']:
        log_signals_to_excel(result['signals'])
        result['excel_saved'] = True
    save_last_scan(result)
    return jsonify(result)

@app.route('/api/last_scan')
@require_auth
def api_last_scan():
    data = load_last_scan()
    return jsonify(data) if data else jsonify({'signals':[],'processed':0,'total':len(NIFTY_TICKERS)})

@app.route('/api/resolve')
@require_admin
def api_resolve():
    resolved = auto_resolve_trades()
    return jsonify({'resolved_count':len(resolved),'resolved':resolved})

@app.route('/api/history')
@require_auth
def api_history():
    if not EXCEL_PATH.exists(): return jsonify({'history':[]})
    try:
        df = pd.read_excel(EXCEL_PATH, sheet_name='Signals Log').fillna('')
        return jsonify({'history':df.to_dict(orient='records')})
    except Exception as e:
        return jsonify({'history':[],'error':str(e)})

@app.route('/api/performance')
@require_auth
def api_performance():
    if not EXCEL_PATH.exists(): return jsonify({})
    try:
        df = pd.read_excel(EXCEL_PATH, sheet_name='Performance').fillna('—')
        return jsonify(dict(zip(df['Metric'], df['Value'])))
    except: return jsonify({})

@app.route('/api/open_excel')
@require_admin
def api_open_excel():
    init_excel()
    try:
        if sys.platform == 'win32': os.startfile(str(EXCEL_PATH))
        elif sys.platform == 'darwin': subprocess.Popen(['open', str(EXCEL_PATH)])
        else: subprocess.Popen(['xdg-open', str(EXCEL_PATH)])
        return jsonify({'success':True})
    except Exception as e:
        return jsonify({'success':False,'error':str(e)})

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
                    'excel_exists':EXCEL_PATH.exists(),
                    'last_scan_time':last.get('timestamp') if last else None,
                    'last_signals':len(last.get('signals',[])) if last else 0,
                    'is_admin': is_admin})

if __name__ == '__main__':
    init_excel()
    print("="*60)
    print(" Stock ML Dashboard v2")
    print("="*60)
    print(f" Model    : {'✅ loaded' if MODEL else '❌ not found'}")
    print(f" Tickers  : {len(NIFTY_TICKERS)}")
    print(f" Excel    : {EXCEL_PATH}")
    print(f"\n Open: http://localhost:5000")
    print("="*60)
    app.run(host='0.0.0.0', port=5000, debug=False)
