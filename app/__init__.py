from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from app.db import init_db
from flask_wtf.csrf import CSRFProtect
import os
import secrets

app = Flask(__name__, static_folder='static')

# SECURITY: Set a random secret key for session signing
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

# SECURITY: Centralized Config for Hardening
app.config['ADMIN_EMAILS'] = [email.strip() for email in os.environ.get('ADMIN_EMAILS', '').split(',') if email.strip()]

@app.context_processor
def inject_firebase_config():
    return dict(firebase_config={
        'apiKey': os.environ.get('FIREBASE_API_KEY', ''),
        'authDomain': os.environ.get('FIREBASE_AUTH_DOMAIN', ''),
        'projectId': os.environ.get('FIREBASE_PROJECT_ID', ''),
        'storageBucket': os.environ.get('FIREBASE_STORAGE_BUCKET', ''),
        'messagingSenderId': os.environ.get('FIREBASE_MESSAGING_SENDER_ID', ''),
        'appId': os.environ.get('FIREBASE_APP_ID', ''),
        'measurementId': os.environ.get('FIREBASE_MEASUREMENT_ID', '')
    })

app.config['ALLOWED_EXTENSIONS'] = set(os.environ.get('ALLOWED_EXTENSIONS', 'pdf,jpg,jpeg,png').lower().split(','))

# Enable CSRF protection globally
csrf = CSRFProtect(app)

# SECURITY: Injection of Security Headers
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    # Adjusted CSP - allows Firebase Auth, Google Identity, and Lucide Icons
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://www.gstatic.com https://apis.google.com https://unpkg.com https://internmitra-ebb77.firebaseapp.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https://*.supabase.co https://lh3.googleusercontent.com https://www.gstatic.com; "
        "connect-src 'self' https://*.supabase.co https://www.googleapis.com https://identitytoolkit.googleapis.com https://securetoken.googleapis.com https://internmitra-ebb77.firebaseapp.com; "
        "frame-src https://internmitra-ebb77.firebaseapp.com https://internmitra-ebb77.firebaseauth.com;"
    )
    return response

try:
    init_db()
except Exception as e:
    app.logger.error(f"Failed to initialize database: {e}")

from app import routes