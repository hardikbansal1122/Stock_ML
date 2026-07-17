#!/usr/bin/env python3
"""
app.py — Stock ML Dashboard v2
- Loads last scan on startup (no more dashes)
- Auto-resolves trades after 5 trading days
- Auto-fills exit price + return in Excel
Run: python app.py
Open: http://localhost:5000
"""

from postgrest import base_request_builder
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
from datetime import datetime, timedelta, timezone, time
from zoneinfo import ZoneInfo
import warnings
warnings.filterwarnings('ignore')

IST_TZ = ZoneInfo("Asia/Kolkata")

app = Flask(__name__, static_folder='static')

BASE_DIR       = Path(__file__).parent
ROOT_DIR       = BASE_DIR.parent
MODEL_PATH     = BASE_DIR / 'xgb_model.pkl'
SCALER_PATH    = BASE_DIR / 'scaler.pkl'
FEAT_PATH      = BASE_DIR / 'feature_list.csv'

sys.path.insert(0, str(ROOT_DIR))
from universe import get_universe_tickers, normalize_ticker


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
    normalize_ticker(t) for t in get_universe_tickers(ROOT_DIR / 'universe' / 'universe.csv')
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
# Updated /api/scan: store scan results with uid and trading_date
@app.route('/api/scan')
@require_auth
def api_scan():
    uid = request.user.get('uid')
    trading_date = get_trading_date()
    
    # Check if user already scanned today
    existing_scan = (supabase
        .table('user_scans')
        .select('id')
        .eq('uid', uid)
        .eq('trading_date', str(trading_date))
        .execute())
    if existing_scan.data:
        return jsonify({"already_scanned": True, "message": "You have already generated today's picks."})
    
    threshold = float(request.args.get('threshold', 0.60))
    result = run_scanner(threshold=threshold)
    
    if supabase and uid:
        scan_time = datetime.now(timezone.utc).isoformat()
        for sig in result.get('signals', []):
            ticker = sig.get('ticker')
            # Insert trade if not duplicate
            dup = (supabase.table('trades')
                .select('id')
                .eq('uid', uid)
                .eq('ticker', ticker)
                .eq('status', 'OPEN')
                .execute())
            if not dup.data:
                supabase.table('trades').insert({
                    'uid': uid,
                    'ticker': ticker,
                    'confidence': sig.get('confidence'),
                    'entry_price': sig.get('close'),
                    'entry_date': datetime.now(timezone.utc).isoformat(),
                    'status': 'OPEN'
                }).execute()
            # Store scan result with uid and scan_time
            supabase.table('scan_results').insert({
                'uid': uid,
                'ticker': ticker,
                'confidence': sig.get('confidence'),
                'price': sig.get('close'),
                'scan_time': scan_time
            }).execute()
        # Mark that this user has scanned today
        supabase.table('user_scans').insert({
            'uid': uid,
            'trading_date': str(trading_date),
            'created_at': scan_time
        }).execute()
    
    # No longer write to a global file
    # save_last_scan(result)  # removed
    return jsonify(result)

# Updated /api/last_scan: return only this user's most recent scan results
@app.route('/api/last_scan')
@require_auth
def api_last_scan():
    uid = request.user.get('uid')
    # Retrieve the latest scan run for this user from user_scans
    latest_scan = supabase.table('user_scans')\
        .select('created_at')\
        .eq('uid', uid)\
        .order('created_at', desc=True)\
        .limit(1)\
        .execute()
    if not latest_scan.data:
        return jsonify({'signals': [], 'processed': 0, 'total': len(NIFTY_TICKERS)})
    
    st = latest_scan.data[0].get('created_at')
    dt_st = datetime.fromisoformat(st.replace('Z', '+00:00'))
    start_time = (dt_st - timedelta(seconds=5)).isoformat()
    end_time = (dt_st + timedelta(seconds=5)).isoformat()
    
    response = supabase.table('scan_results')\
        .select('*')\
        .eq('uid', uid)\
        .gte('scan_time', start_time)\
        .lte('scan_time', end_time)\
        .order('id', desc=True)\
        .execute()
        
    signals = []
    for row in response.data or []:
        signals.append({
            'ticker': row['ticker'],
            'confidence': float(row['confidence']),
            'close': float(row['price']),
            'rsi': 50,
            'volume_ratio': 1.0,
            'momentum_5d': 0
        })
    
    dt_ist = dt_st.astimezone(IST_TZ)
    scan_date = dt_ist.strftime("%d %b %Y")
    scan_time = dt_ist.strftime("%I:%M %p")

    return jsonify({
        'signals': signals,
        'processed': len(signals),
        'total': len(NIFTY_TICKERS),
        'date': scan_date,
        'time': scan_time
    })

def load_last_scan():
    return None

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

def get_trading_date():

    ist = ZoneInfo("Asia/Kolkata")
    now = datetime.now(ist)

    market_open = time(9, 15)

    if now.time() < market_open:
        return (now.date() - timedelta(days=1))

    return now.date()

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

@app.route('/api/resolve')
@require_auth
def api_resolve():
    resolved = auto_resolve_trades()
    return jsonify({'resolved_count':len(resolved),'resolved':resolved})

@app.route('/api/history')
@require_auth
def api_history():

    uid = request.user.get('uid')

    try:

        print("HISTORY UID:", uid)

        response = (
            supabase
            .table('trades')
            .select('*')
            .eq('uid', uid)
            .order('entry_date', desc=True)
            .execute()
        )

        print("HISTORY RESPONSE:", response.data)

        return jsonify({
            'history': response.data or []
        })

    except Exception as e:

        print("HISTORY ERROR:", str(e))

        return jsonify({
            'history': [],
            'error': str(e)
        }), 500


@app.route('/api/status')
@require_auth
def api_status():
    print("API_STATUS CALLED")
    
    user = request.user
    uid = user.get('uid')
    email = user.get('email')
    
    # Determine admin status
    is_admin = False
    if email in ADMIN_EMAILS:
        is_admin = True
    elif supabase:
        try:
            res = supabase.table('users').select('role').eq('uid', uid).execute()
            if res.data and len(res.data) > 0 and res.data[0].get('role') == 'admin':
                is_admin = True
        except Exception:
            pass
    print("\n=== ADMIN DEBUG ===")
    print("EMAIL:", email)
    print("UID:", uid)
    print("ADMIN_EMAILS:", ADMIN_EMAILS)
    print("IS_ADMIN:", is_admin)
    print("===================\n")
    
    # Fetch the most recent scan timestamp for this user
    last_scan_time = None
    if supabase:
        try:
            resp = supabase.table('user_scans')\
                .select('created_at')\
                .eq('uid', uid)\
                .order('created_at', desc=True)\
                .limit(1)\
                .execute()
            if resp.data:
                raw_time = resp.data[0].get('created_at')
                dt = datetime.fromisoformat(raw_time.replace('Z', '+00:00'))
                dt_ist = dt.astimezone(IST_TZ)
                last_scan_time = dt_ist.strftime("%d %b %Y, %I:%M %p")
        except Exception:
            pass
    
    print("\n=== ADMIN DEBUG ===")
    print("EMAIL:", email)
    print("UID:", uid)
    print("ADMIN_EMAILS:", ADMIN_EMAILS)

    if supabase:
        try:
            dbg = supabase.table('users').select('role').eq('uid', uid).execute()
            print("DB ROLE:", dbg.data)
        except Exception as e:
            print("ROLE ERROR:", e)

    print("FINAL is_admin:", is_admin)
    print("===================\n")
    return jsonify({
        'model_loaded': MODEL is not None,
        'total_tickers': len(NIFTY_TICKERS),
        'storage': 'supabase',
        'last_scan_time': last_scan_time,
        'last_signals': 0,  # signals count now obtained via /api/last_scan per‑user
        'is_admin': is_admin
    })

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


@app.route('/api/can_scan')
@require_auth
def api_can_scan():

    uid = request.user.get('uid')
    trading_date = get_trading_date()

    existing_scan = (
        supabase
        .table('user_scans')
        .select('id')
        .eq('uid', uid)
        .eq('trading_date', str(trading_date))
        .execute()
    )

    return jsonify({
        'can_scan': len(existing_scan.data) == 0
    })
        


# ── Admin Routes ───────────────────────────────────────────────────────────

@app.route('/api/admin/overview')
@require_admin
def api_admin_overview():
    """Platform-wide metrics for admin overview."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500

    try:
        # Total approved users
        users_resp = supabase.table('approved_users').select('*').execute()
        total_users = len(users_resp.data or [])

        # Total scans (unique user+date pairs)
        scans_resp = supabase.table('user_scans').select('uid, trading_date').execute()
        total_scans = len(scans_resp.data or [])

        # Total trades
        trades_resp = supabase.table('trades').select('id, status, return_pct').execute()
        all_trades = trades_resp.data or []
        total_trades = len(all_trades)
        closed_trades = [t for t in all_trades if t.get('status') == 'CLOSED']
        wins = [t for t in closed_trades if (t.get('return_pct') or 0) > 0]
        platform_winrate = round((len(wins) / len(closed_trades)) * 100, 1) if closed_trades else None

        # Active users (scanned in last 7 days)
        seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        recent_scans = supabase.table('user_scans').select('uid').gte('created_at', seven_days_ago).execute()
        active_uids = set(r['uid'] for r in (recent_scans.data or []))
        active_users = len(active_uids)

        # Pending access requests
        try:
            req_resp = supabase.table('access_requests').select('id').eq('status', 'pending').execute()
            pending_requests = len(req_resp.data or [])
        except Exception:
            pending_requests = 0

        # Today's scans
        today = str(get_trading_date())
        today_scans_resp = supabase.table('user_scans').select('uid').eq('trading_date', today).execute()
        today_scan_count = len(today_scans_resp.data or [])

        return jsonify({
            'total_users': total_users,
            'active_users': active_users,
            'total_scans': total_scans,
            'today_scan_count': today_scan_count,
            'total_trades': total_trades,
            'closed_trades': len(closed_trades),
            'platform_winrate': platform_winrate,
            'pending_requests': pending_requests,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/users')
@require_admin
def api_admin_users():
    """List all users with their activity summary."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500

    try:
        # Get approved users
        approved_resp = supabase.table('approved_users').select('*').execute()
        approved_emails = {r['email']: r for r in (approved_resp.data or [])}

        # Get users table (has uid, email, role, display_name, last_login)
        users_resp = supabase.table('users').select('*').order('last_login', desc=True).execute()
        users = users_resp.data or []

        # Get scan counts per user
        scans_resp = supabase.table('user_scans').select('uid, trading_date').execute()
        scan_counts = {}
        for s in (scans_resp.data or []):
            uid = s['uid']
            scan_counts[uid] = scan_counts.get(uid, 0) + 1

        # Get trade counts per user
        trades_resp = supabase.table('trades').select('uid, status').execute()
        trade_counts = {}
        for t in (trades_resp.data or []):
            uid = t['uid']
            trade_counts[uid] = trade_counts.get(uid, 0) + 1

        result = []
        for u in users:
            uid = u.get('uid')
            email = u.get('email', '')
            is_admin_user = False
            if email and email.strip().lower() in [a.lower() for a in ADMIN_EMAILS]:
                is_admin_user = True
            elif u.get('role') == 'admin':
                is_admin_user = True

            is_approved = email.lower() in {k.lower() for k in approved_emails}

            result.append({
                'uid': uid,
                'email': email,
                'display_name': u.get('display_name', ''),
                'role': 'admin' if is_admin_user else u.get('role', 'user'),
                'last_login': u.get('last_login'),
                'scan_count': scan_counts.get(uid, 0),
                'trade_count': trade_counts.get(uid, 0),
                'is_approved': is_approved,
                'is_founder': email.strip().lower() in [a.lower() for a in ADMIN_EMAILS],
            })

        return jsonify({'users': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/users/<uid>/role', methods=['POST'])
@require_admin
def api_admin_set_role(uid):
    """Grant or revoke admin role for a user."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500

    acting_email = request.user.get('email', '')
    data = request.get_json(force=True)
    new_role = data.get('role', 'user')

    # Lookup target user email
    try:
        target_resp = supabase.table('users').select('email').eq('uid', uid).execute()
        if not target_resp.data:
            return jsonify({'error': 'User not found'}), 404
        target_email = target_resp.data[0].get('email', '')

        # Prevent founder from being demoted
        if target_email.strip().lower() in [a.lower() for a in ADMIN_EMAILS] and new_role != 'admin':
            return jsonify({'error': 'Cannot revoke founder admin access'}), 403

        supabase.table('users').update({'role': new_role}).eq('uid', uid).execute()
        print(f"ADMIN: {acting_email} set uid={uid} role to {new_role}")
        return jsonify({'status': 'success', 'role': new_role})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/users/<uid>/revoke', methods=['POST'])
@require_admin
def api_admin_revoke_user(uid):
    """Remove a user from the approved_users list (blocks their access)."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500

    acting_email = request.user.get('email', '')

    try:
        target_resp = supabase.table('users').select('email').eq('uid', uid).execute()
        if not target_resp.data:
            return jsonify({'error': 'User not found'}), 404
        target_email = target_resp.data[0].get('email', '')

        # Protect founders
        if target_email.strip().lower() in [a.lower() for a in ADMIN_EMAILS]:
            return jsonify({'error': 'Cannot revoke founder access'}), 403

        supabase.table('approved_users').delete().ilike('email', target_email).execute()
        print(f"ADMIN: {acting_email} revoked access for {target_email}")
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Access Requests ────────────────────────────────────────────────────────

@app.route('/api/request_access', methods=['POST'])
def api_request_access():
    """Allow any user to submit an access request (no auth required beyond valid Firebase token)."""
    from firebase_admin import auth as fb_auth
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Unauthorized'}), 401

    token = auth_header.split(' ')[1]
    try:
        decoded = fb_auth.verify_id_token(token)
    except Exception as e:
        return jsonify({'error': 'Invalid token', 'details': str(e)}), 401

    email = decoded.get('email', '')
    uid = decoded.get('uid', '')
    display_name = decoded.get('name', '')
    data = request.get_json(force=True) or {}
    reason = str(data.get('reason', ''))[:500]

    if not supabase:
        return jsonify({'error': 'Database unavailable'}), 500

    try:
        # Check if already approved
        approved = supabase.table('approved_users').select('id').ilike('email', email).execute()
        if approved.data:
            return jsonify({'status': 'already_approved'})

        # Check if request already pending
        existing = supabase.table('access_requests').select('id, status').eq('uid', uid).execute()
        if existing.data:
            latest = existing.data[-1]
            if latest.get('status') == 'pending':
                return jsonify({'status': 'already_pending'})

        supabase.table('access_requests').insert({
            'uid': uid,
            'email': email,
            'display_name': display_name,
            'reason': reason,
            'status': 'pending',
            'created_at': datetime.now(timezone.utc).isoformat()
        }).execute()

        return jsonify({'status': 'submitted'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/requests')
@require_admin
def api_admin_requests():
    """List all pending access requests."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500

    try:
        resp = supabase.table('access_requests').select('*').order('created_at', desc=True).execute()
        return jsonify({'requests': resp.data or []})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/requests/<req_id>/approve', methods=['POST'])
@require_admin
def api_admin_approve_request(req_id):
    """Approve an access request — adds email to approved_users."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500

    acting_email = request.user.get('email', '')
    try:
        req_resp = supabase.table('access_requests').select('*').eq('id', req_id).execute()
        if not req_resp.data:
            return jsonify({'error': 'Request not found'}), 404

        req = req_resp.data[0]
        email = req.get('email', '')

        # Add to approved_users (idempotent)
        existing = supabase.table('approved_users').select('id').ilike('email', email).execute()
        if not existing.data:
            supabase.table('approved_users').insert({'email': email}).execute()

        supabase.table('access_requests').update({
            'status': 'approved',
            'reviewed_at': datetime.now(timezone.utc).isoformat(),
            'reviewed_by': acting_email
        }).eq('id', req_id).execute()

        print(f"ADMIN: {acting_email} approved access for {email}")
        return jsonify({'status': 'approved'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/requests/<req_id>/reject', methods=['POST'])
@require_admin
def api_admin_reject_request(req_id):
    """Reject an access request."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500

    acting_email = request.user.get('email', '')
    try:
        supabase.table('access_requests').update({
            'status': 'rejected',
            'reviewed_at': datetime.now(timezone.utc).isoformat(),
            'reviewed_by': acting_email
        }).eq('id', req_id).execute()

        print(f"ADMIN: {acting_email} rejected request id={req_id}")
        return jsonify({'status': 'rejected'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':

    print("="*60)
    print(" Stock ML Dashboard v2")
    print("="*60)
    print(f" Model    : {'✅ loaded' if MODEL else '❌ not found'}")
    print(f" Tickers  : {len(NIFTY_TICKERS)}")
    print(f"\n Open: http://localhost:5000")
    print("="*60)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

