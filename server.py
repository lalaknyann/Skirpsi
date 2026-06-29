import os
import json
import datetime
import bcrypt
import jwt
from flask import Flask, request, jsonify, send_from_directory, redirect, make_response

app = Flask(__name__, static_folder=None) # Disable default static serving to prevent direct path bypass
SECRET_KEY = "indibiz-ml-secret-key-skripsi-2026"
DASHBOARD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard")

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
    try:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")
        
        if not username or not password:
            return jsonify({"success": False, "message": "Username dan password harus diisi"}), 400
            
        credentials = load_credentials()
        
        if username.lower() != credentials["username"].lower():
            return jsonify({"success": False, "message": "Username atau password salah"}), 401
            
        # Verify hash
        hashed_password = credentials["password_hash"].encode('utf-8')
        if bcrypt.checkpw(password.encode('utf-8'), hashed_password):
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
            return jsonify({"success": False, "message": "Username atau password salah"}), 401
            
    except Exception as e:
        return jsonify({"success": False, "message": f"Terjadi kesalahan server: {str(e)}"}), 500

@app.route("/api/logout", methods=["POST"])
def logout():
    resp = make_response(jsonify({"success": True, "message": "Logout berhasil"}))
    resp.set_cookie("auth_token", "", expires=0)
    return resp

@app.route("/api/verify", methods=["GET"])
def verify():
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
