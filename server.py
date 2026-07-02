import os
import json
import datetime
import bcrypt
import jwt
import secrets
from datetime import timedelta
from flask import Flask, request, jsonify, send_from_directory, redirect, make_response, session

app = Flask(__name__, static_folder=None) # Disable default static serving to prevent direct path bypass

# B2. KEAMANAN SESSION FLASK
app.secret_key = secrets.token_hex(32)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,  
    SESSION_COOKIE_SAMESITE='Lax', 
    PERMANENT_SESSION_LIFETIME=timedelta(hours=2)
)

SECRET_KEY = "indibiz-ml-secret-key-skripsi-2026"
DASHBOARD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard")

# B4. LIMIT PERCOBAAN LOGIN — ANTI BRUTE FORCE
login_attempts = {}  # { ip: { count, last_attempt } }

def load_credentials():
    cred_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "credentials.json")
    with open(cred_path, "r") as f:
        return json.load(f)

def verify_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# Middleware to check auth on routes
def is_authenticated():
    if 'user' not in session:
        return False
        
    token = request.cookies.get("auth_token")
    if not token:
        # Also check Authorization Header as fallback
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
    
    if not token:
        return False
    
    payload = verify_token(token)
    return payload is not None

# ─── AUTHENTICATION API ENDPOINTS ───

@app.route("/api/login", methods=["POST"])
def login():
    ip = request.remote_addr
    now = datetime.datetime.utcnow()
    
    # B4. Cek apakah IP sedang diblokir
    if ip in login_attempts:
        attempts = login_attempts[ip]
        if attempts["count"] >= 5:
            time_passed = now - attempts["last_attempt"]
            if time_passed < datetime.timedelta(minutes=5):
                return jsonify({"success": False, "message": "Terlalu banyak percobaan. Coba lagi dalam 5 menit."}), 429
            else:
                # 5 menit sudah berlalu, reset hitungan
                login_attempts.pop(ip)

    try:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")
        
        if not username or not password:
            return jsonify({"success": False, "message": "Username dan password harus diisi"}), 400
            
        credentials = load_credentials()
        
        # Helper function to record a failed attempt
        def record_failure():
            if ip not in login_attempts:
                login_attempts[ip] = {"count": 1, "last_attempt": now}
            else:
                attempts = login_attempts[ip]
                # Jika percobaan gagal terakhir lebih dari 5 menit lalu, reset ke 1
                if now - attempts["last_attempt"] >= datetime.timedelta(minutes=5):
                    attempts["count"] = 1
                else:
                    attempts["count"] += 1
                attempts["last_attempt"] = now
        
        if username.lower() != credentials["username"].lower():
            record_failure()
            count = login_attempts[ip]["count"]
            if count >= 5:
                return jsonify({"success": False, "message": "Terlalu banyak percobaan. Coba lagi dalam 5 menit."}), 429
            return jsonify({"success": False, "message": "Username atau password salah"}), 401
            
        # Verify hash
        hashed_password = credentials["password_hash"].encode('utf-8')
        if bcrypt.checkpw(password.encode('utf-8'), hashed_password):
            # Reset attempts on success
            if ip in login_attempts:
                login_attempts.pop(ip)
                
            # Set Flask session
            session['user'] = username
            session.permanent = True
            
            # Generate JWT Token (valid for 8 hours)
            expiration = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
            token = jwt.encode(
                {"username": username, "exp": expiration},
                SECRET_KEY,
                algorithm="HS256"
            )
            
            # Send response with HTTPOnly Cookie for security
            resp = make_response(jsonify({"success": True, "token": token, "message": "Login berhasil"}))
            # Cookie expires in 8 hours (28800 seconds)
            resp.set_cookie("auth_token", token, httponly=True, max_age=28800, samesite="Lax")
            return resp
        else:
            record_failure()
            count = login_attempts[ip]["count"]
            if count >= 5:
                return jsonify({"success": False, "message": "Terlalu banyak percobaan. Coba lagi dalam 5 menit."}), 429
            return jsonify({"success": False, "message": "Username atau password salah"}), 401
            
    except Exception as e:
        return jsonify({"success": False, "message": f"Terjadi kesalahan server: {str(e)}"}), 500

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear() # B2. Bersihkan Flask session
    resp = make_response(jsonify({"success": True, "message": "Logout berhasil"}))
    resp.set_cookie("auth_token", "", max_age=0, httponly=True, samesite="Lax", path="/")
    return resp

@app.route("/api/verify", methods=["GET"])
def verify():
    if 'user' not in session or not is_authenticated():
        return jsonify({"success": False, "message": "Session tidak valid atau expired"}), 401
        
    token = request.cookies.get("auth_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            
    if not token:
        return jsonify({"success": False, "message": "Token tidak ditemukan"}), 401
        
    payload = verify_token(token)
    if payload:
        return jsonify({"success": True, "username": payload["username"]})
    else:
        return jsonify({"success": False, "message": "Token tidak valid atau kedaluwarsa"}), 401

# B3. PROTEKSI FILE CSV LEWAT FLASK ROUTE TERPROTEKSI
@app.route("/data/<path:filename>")
def serve_protected_csv(filename):
    if 'user' not in session or not is_authenticated():
        return jsonify({"error": "Unauthorized"}), 401
        
    safe_filename = os.path.basename(filename)
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    return send_from_directory(data_dir, safe_filename)

# ─── FRONTEND ROUTES & STATIC FILES SERVING ───

@app.route("/login")
def serve_login_page():
    # If already logged in, redirect to dashboard
    if is_authenticated():
        return redirect("/")
    return send_from_directory(DASHBOARD_DIR, "login.html")

@app.route("/")
@app.route("/index.html")
def serve_index_page():
    # If not logged in, redirect to login page
    if not is_authenticated():
        return redirect("/login")
    return send_from_directory(DASHBOARD_DIR, "index.html")

# Serve other static files (css, js, images, data, etc.)
@app.route("/<path:filename>")
def serve_static(filename):
    # Prevent directory traversal
    safe_path = os.path.normpath(filename)
    if safe_path.startswith("..") or os.path.isabs(safe_path):
        return jsonify({"error": "Forbidden"}), 403
        
    # If they are requesting html files directly (other than login.html), make sure they are authenticated
    if filename.endswith(".html") and filename != "login.html":
        if not is_authenticated():
            return redirect("/login")
            
    return send_from_directory(DASHBOARD_DIR, filename)

if __name__ == "__main__":
    print("--------------------------------------------------")
    print("Indibiz ML Dashboard Backend Server is running!")
    print("URL: http://localhost:8000")
    print("--------------------------------------------------")
    app.run(host="0.0.0.0", port=8000, debug=True)
