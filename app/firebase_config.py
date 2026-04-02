
import firebase_admin
from firebase_admin import credentials, auth
import os

# Create credentials object
service_account_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
cred = None

if service_account_json:
    try:
        import json
        service_account_info = json.loads(service_account_json)
        cred = credentials.Certificate(service_account_info)
    except Exception as e:
        print(f"Error loading FIREBASE_SERVICE_ACCOUNT from env: {e}")
        if os.path.exists("serviceAccountKey.json"):
            cred = credentials.Certificate("serviceAccountKey.json")
else:
    # Fallback to local file for development
    if os.path.exists("serviceAccountKey.json"):
        cred = credentials.Certificate("serviceAccountKey.json")

# Initialize app if not already done
if not firebase_admin._apps:
    try:
        if cred:
            firebase_admin.initialize_app(cred)
        else:
            print("WARNING: No Firebase credentials found. verify_token will fail.")
    except Exception as e:
        print(f"FAILED TO INITIALIZE FIREBASE: {e}")

import time

def verify_token(id_token):
    # Try twice to handle minor clock skew ("Token used too early")
    for attempt in range(2):
        try:
            # Use built-in clock skew support (10 seconds leeway)
            decoded_token = auth.verify_id_token(id_token, clock_skew_seconds=10)
            return decoded_token, None
        except Exception as e:
            error_msg = str(e)
            # If token is used too early despite leeway, wait a moment and retry once
            if "Token used too early" in error_msg and attempt == 0:
                print(f"Clock skew detected ({error_msg}), retrying in 2s...")
                time.sleep(2)
                continue
            
            print(f"Error verifying token: {error_msg}")
            return None, error_msg
