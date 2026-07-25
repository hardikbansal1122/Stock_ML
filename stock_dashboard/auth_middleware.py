import os
import json
import functools
from time import perf_counter
from flask import request, jsonify, g
from firebase_admin import auth, credentials, initialize_app
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

LOCAL_DEV = os.getenv("LOCAL_DEV", "false").lower() == "true"
print(f"LOCAL_DEV = {LOCAL_DEV}")


def _set_local_dev_user():
    request.user = {
        "email": "local@stockml.dev",
        "uid": "local-dev",
        "name": "Local Dev",
    }

# Initialize Firebase Admin
try:
    firebase_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")

    if firebase_json:
        cred_dict = json.loads(firebase_json)
        cred = credentials.Certificate(cred_dict)
        initialize_app(cred)
        print("✅ Firebase initialized from Railway environment variable")
    else:
        print("❌ FIREBASE_SERVICE_ACCOUNT_JSON not found")

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
        if not hasattr(g, "performance"):
            g.performance = {}

        if LOCAL_DEV:
            _set_local_dev_user()
            return f(*args, **kwargs)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Unauthorized"}), 401
        
        token = auth_header.split(" ")[1]
        try:
            auth_start = perf_counter()
            decoded_token = auth.verify_id_token(token)
            auth_end = perf_counter()
            g.performance["authentication"] = g.performance.get("authentication", 0.0) + (auth_end - auth_start)
            print("=" * 50)
            print("EMAIL FROM FIREBASE:", decoded_token.get("email"))
            print("FULL TOKEN:", decoded_token)
            print("=" * 50)
            email = decoded_token.get("email")
            print("DEBUG AUTH - Email from token:", email, flush=True)
            print("DEBUG AUTH - Supabase client:", supabase, flush=True)

            if supabase and email:
                # Use .ilike for case-insensitive email search
                lookup_start = perf_counter()
                response = (
                    supabase
                    .table("approved_users")
                    .select("*")
                    .ilike("email", email.strip())
                    .execute()
                )
                lookup_end = perf_counter()
                g.performance["supabase_user_lookup"] = g.performance.get("supabase_user_lookup", 0.0) + (lookup_end - lookup_start)

                print("FULL TABLE:", response.data)
                print("EMAIL:", repr(email))
                print("QUERY RESULT:", response.data)
                print("DEBUG AUTH - Supabase response data:", response.data, flush=True)
                if not response.data:
                    return jsonify({
                        "error": "Access denied",
                        "message": "Your email is not approved."
                    }), 403
            elif not email:
                print("DEBUG AUTH - No email found in token!", flush=True)
                return jsonify({
                    "error": "Access denied",
                    "message": "No email associated with this account."
                }), 403

            request.user = decoded_token

        except Exception as e:
            print("DEBUG AUTH - Exception occurred:", str(e), flush=True)
            return jsonify({"error": "Invalid token", "details": str(e)}), 401
            
        return f(*args, **kwargs)
    return decorated_function

def require_admin(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if LOCAL_DEV:
            _set_local_dev_user()
            return f(*args, **kwargs)

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
            
            # Check whitelist first (case-insensitive)
            if email and email.strip().lower() in [admin.lower() for admin in ADMIN_EMAILS]:
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
