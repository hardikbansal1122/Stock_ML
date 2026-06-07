import os
import functools
from flask import request, jsonify
from firebase_admin import auth, credentials, initialize_app
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Initialize Firebase Admin
cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase_credentials.json")
try:
    if os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        initialize_app(cred)
    else:
        print(f"Warning: {cred_path} not found. Firebase Admin not initialized.")
except Exception as e:
    print(f"Firebase Admin init failed: {e}")

# Initialize Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
ADMIN_EMAILS = [email.strip() for email in os.getenv("ADMIN_EMAILS", "").split(",") if email.strip()]

supabase: Client = None
if SUPABASE_URL and SUPABASE_SERVICE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    except Exception as e:
        print(f"Supabase init failed: {e}")

def require_auth(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Unauthorized"}), 401
        
        token = auth_header.split(" ")[1]
        try:
            decoded_token = auth.verify_id_token(token)
            request.user = decoded_token
        except Exception as e:
            return jsonify({"error": "Invalid token", "details": str(e)}), 401
            
        return f(*args, **kwargs)
    return decorated_function

def require_admin(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Unauthorized"}), 401
        
        token = auth_header.split(" ")[1]
        try:
            decoded_token = auth.verify_id_token(token)
            request.user = decoded_token
            
            email = decoded_token.get("email")
            uid = decoded_token.get("uid")
            
            is_admin = False
            
            # Check whitelist first
            if email in ADMIN_EMAILS:
                is_admin = True
            elif supabase:
                # Check database role
                response = supabase.table("users").select("role").eq("uid", uid).execute()
                if response.data and len(response.data) > 0:
                    if response.data[0].get("role") == "admin":
                        is_admin = True
            
            if not is_admin:
                return jsonify({"error": "Forbidden: Admin access required"}), 403
                
        except Exception as e:
            return jsonify({"error": "Invalid token", "details": str(e)}), 401
            
        return f(*args, **kwargs)
    return decorated_function
