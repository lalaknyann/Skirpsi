import os
import json
import datetime
import bcrypt
import jwt
import secrets
from datetime import timedelta
from flask import Flask, request, jsonify, send_from_directory, redirect, make_response, session
import joblib
import numpy as np
import pandas as pd

app = Flask(__name__, static_folder=None) # Disable default static serving to prevent direct path bypass

# Load models and scalers at startup
MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")

views_only_scaler = None
views_only_models = {}

try:
    views_only_scaler = joblib.load(os.path.join(MODELS_DIR, "views_only_scaler.joblib"))
    views_only_models = {
        "Linear Regression": joblib.load(os.path.join(MODELS_DIR, "views_only_ridge.joblib")),
        "Random Forest": joblib.load(os.path.join(MODELS_DIR, "views_only_rf.joblib")),
        "XGBoost": joblib.load(os.path.join(MODELS_DIR, "views_only_xgb.joblib"))
    }
    print("✅ Views-Only models and scaler loaded successfully!")
except Exception as e:
    print(f"⚠️ Error loading Views-Only models: {e}")

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
        
        user_list = credentials.get("users", [])
        user_data = None
        for u in user_list:
            if u["username"].lower() == username.lower():
                user_data = u
                break
                
        if not user_data:
            record_failure()
            count = login_attempts[ip]["count"]
            if count >= 5:
                return jsonify({"success": False, "message": "Terlalu banyak percobaan. Coba lagi dalam 5 menit."}), 429
            return jsonify({"success": False, "message": "Username atau password salah"}), 401
            
        # Verify hash
        hashed_password = user_data["password_hash"].encode('utf-8')
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

# ─── ML PREDICTIONS & METRICS API ENDPOINTS ───

@app.route("/api/predict", methods=["POST"])
def predict_single():
    if 'user' not in session or not is_authenticated():
        return jsonify({"error": "Unauthorized"}), 401
    try:
        data = request.get_json()
        fb = float(data.get("fb", 0))
        ig = float(data.get("ig", 0))
        tt = float(data.get("tt", 0))
        tanggal_str = data.get("tanggal", "")
        
        # Parse date
        if tanggal_str:
            try:
                bulan_id = {
                    'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
                    'Mei': '05', 'Jun': '06', 'Jul': '07', 'Agu': '08',
                    'Sep': '09', 'Okt': '10', 'Nov': '11', 'Des': '12'
                }
                tgl_clean = tanggal_str
                for id_name, num in bulan_id.items():
                    tgl_clean = tgl_clean.replace(id_name, num)
                dt = pd.to_datetime(tgl_clean, errors='coerce')
                if pd.isna(dt):
                    dt = pd.to_datetime(datetime.date.today())
            except Exception:
                dt = pd.to_datetime(datetime.date.today())
        else:
            dt = pd.to_datetime(datetime.date.today())
            
        # Extract temporal features
        hari = dt.day
        bulan = dt.month
        tahun = dt.year
        hari_pekan = dt.dayofweek
        is_weekend = 1 if hari_pekan >= 5 else 0
        quarter = dt.quarter
        day_of_year = dt.timetuple().tm_yday
        week_of_year = dt.isocalendar()[1]
        
        # Cyclical
        bulan_sin = np.sin(2 * np.pi * bulan / 12)
        bulan_cos = np.cos(2 * np.pi * bulan / 12)
        dow_sin = np.sin(2 * np.pi * hari_pekan / 7)
        dow_cos = np.cos(2 * np.pi * hari_pekan / 7)
        
        # Months flags
        is_peak_month = 1 if bulan in [3, 4, 12] else 0
        is_mid_year = 1 if bulan in [6, 7] else 0
        is_q4 = 1 if quarter == 4 else 0
        
        # Views features
        log_facebook = np.log1p(fb)
        log_instagram = np.log1p(ig)
        log_tiktok = np.log1p(tt)
        total_views = fb + ig + tt
        log_total_views = np.log1p(total_views)
        ratio_fb_total = fb / (total_views + 1)
        ratio_ig_total = ig / (total_views + 1)
        ratio_tt_total = tt / (total_views + 1)
        
        # Lags/rolling defaults (since history is not available for single prediction)
        facebook_growth = 0.0
        instagram_growth = 0.0
        tiktok_growth = 0.0
        total_views_growth = 0.0
        fb_lag1, fb_lag3, fb_lag7 = fb, fb, fb
        ig_lag1, ig_lag3, ig_lag7 = ig, ig, ig
        tt_lag1, tt_lag3, tt_lag7 = tt, tt, tt
        views_roll7_mean = total_views
        views_roll14_mean = total_views
        views_roll7_std = 0.0
        views_trend = 0.0
        log_views_x_weekend = log_total_views * is_weekend
        log_views_x_peakmon = log_total_views * is_peak_month
        log_views_x_q4 = log_total_views * is_q4
        
        # Combine into dict matching get_views_only_feature_columns
        from ml_indibiz.preprocessing import get_views_only_feature_columns
        cols = get_views_only_feature_columns()
        
        feat_dict = {
            'Facebook': fb, 'Instagram': ig, 'TikTok': tt,
            'log_facebook': log_facebook, 'log_instagram': log_instagram, 'log_tiktok': log_tiktok,
            'total_views': total_views, 'log_total_views': log_total_views,
            'ratio_fb_total': ratio_fb_total, 'ratio_ig_total': ratio_ig_total, 'ratio_tt_total': ratio_tt_total,
            'facebook_growth': facebook_growth, 'instagram_growth': instagram_growth, 
            'tiktok_growth': tiktok_growth, 'total_views_growth': total_views_growth,
            'hari': hari, 'bulan': bulan, 'tahun': tahun, 'hari_pekan': hari_pekan, 'is_weekend': is_weekend,
            'quarter': quarter, 'day_of_year': day_of_year, 'week_of_year': week_of_year,
            'bulan_sin': bulan_sin, 'bulan_cos': bulan_cos, 'dow_sin': dow_sin, 'dow_cos': dow_cos,
            'is_peak_month': is_peak_month, 'is_mid_year': is_mid_year, 'is_q4': is_q4,
            'fb_lag1': fb_lag1, 'fb_lag3': fb_lag3, 'fb_lag7': fb_lag7,
            'ig_lag1': ig_lag1, 'ig_lag3': ig_lag3, 'ig_lag7': ig_lag7,
            'tt_lag1': tt_lag1, 'tt_lag3': tt_lag3, 'tt_lag7': tt_lag7,
            'views_roll7_mean': views_roll7_mean, 'views_roll14_mean': views_roll14_mean, 
            'views_roll7_std': views_roll7_std, 'views_trend': views_trend,
            'log_views_x_weekend': log_views_x_weekend, 'log_views_x_peakmon': log_views_x_peakmon, 
            'log_views_x_q4': log_views_x_q4
        }
        
        # Order values matching cols
        feat_vals = [feat_dict[c] for c in cols]
        
        # Scale and predict
        if views_only_scaler is not None and views_only_models:
            X_scaled = views_only_scaler.transform([feat_vals])
            lr_pred = float(np.clip(views_only_models["Linear Regression"].predict(X_scaled)[0], 0, 3))
            rf_pred = float(np.clip(views_only_models["Random Forest"].predict(X_scaled)[0], 0, 3))
            xgb_pred = float(np.clip(views_only_models["XGBoost"].predict(X_scaled)[0], 0, 3))
            avg_pred = (lr_pred + rf_pred + xgb_pred) / 3.0
            
            classify = lambda val: 'Tinggi' if val >= 2 else 'Rendah'
            
            return jsonify({
                "lr": {"value": lr_pred, "rounded": int(round(lr_pred)), "class": classify(lr_pred)},
                "rf": {"value": rf_pred, "rounded": int(round(rf_pred)), "class": classify(rf_pred)},
                "xgb": {"value": xgb_pred, "rounded": int(round(xgb_pred)), "class": classify(xgb_pred)},
                "avg": avg_pred
            })
        else:
            return jsonify({"error": "Model not loaded"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/predict-batch", methods=["POST"])
def predict_batch():
    if 'user' not in session or not is_authenticated():
        return jsonify({"error": "Unauthorized"}), 401
    try:
        data = request.get_json()
        rows = data.get("rows", [])
        if not rows:
            return jsonify({"error": "No rows provided"}), 400
            
        # Parse into DataFrame
        df_input = pd.DataFrame(rows)
        
        # Ensure correct casing for required keys
        col_rename = {}
        for c in df_input.columns:
            if c.lower() == 'facebook': col_rename[c] = 'Facebook'
            elif c.lower() == 'instagram': col_rename[c] = 'Instagram'
            elif c.lower() == 'tiktok': col_rename[c] = 'TikTok'
            elif c.lower() == 'tanggal': col_rename[c] = 'tanggal'
            elif c.lower() == 'penjualan': col_rename[c] = 'Penjualan'
            elif c.lower() == 'id': col_rename[c] = 'id'
        df_input = df_input.rename(columns=col_rename)
        
        # Fill Penjualan with 0 if missing (so feature engineering works)
        if 'Penjualan' not in df_input.columns:
            df_input['Penjualan'] = 0.0
        df_input['Penjualan'] = pd.to_numeric(df_input['Penjualan'], errors='coerce').fillna(0.0)
        
        for col in ['Facebook', 'Instagram', 'TikTok']:
            if col in df_input.columns:
                df_input[col] = pd.to_numeric(df_input[col], errors='coerce').fillna(0.0)
            else:
                df_input[col] = 0.0
                
        # Parse dates
        bulan_id = {
            'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
            'Mei': '05', 'Jun': '06', 'Jul': '07', 'Agu': '08',
            'Sep': '09', 'Okt': '10', 'Nov': '11', 'Des': '12'
        }
        def parse_tgl(s):
            s = str(s).strip()
            for id_name, num in bulan_id.items():
                s = s.replace(id_name, num)
            try:
                return pd.to_datetime(s, format='%d %m %Y')
            except Exception:
                try:
                    return pd.to_datetime(s, infer_datetime_format=True)
                except Exception:
                    return pd.NaT
                    
        df_input['tanggal_dt'] = df_input['tanggal'].apply(parse_tgl)
        df_input['tanggal_dt'] = df_input['tanggal_dt'].fillna(pd.to_datetime(datetime.date.today()))
        
        # Store original index to maintain order in predictions response
        df_input['orig_index'] = range(len(df_input))
        
        # Sort by date for proper lag/rolling computation
        df_sorted = df_input.sort_values('tanggal_dt').reset_index(drop=True)
        
        # 1. Temporal
        df_sorted['hari']        = df_sorted['tanggal_dt'].dt.day
        df_sorted['bulan']       = df_sorted['tanggal_dt'].dt.month
        df_sorted['tahun']       = df_sorted['tanggal_dt'].dt.year
        df_sorted['hari_pekan']  = df_sorted['tanggal_dt'].dt.dayofweek
        df_sorted['is_weekend']  = (df_sorted['hari_pekan'] >= 5).astype(int)
        df_sorted['quarter']     = df_sorted['tanggal_dt'].dt.quarter
        df_sorted['day_of_year'] = df_sorted['tanggal_dt'].dt.dayofyear
        df_sorted['week_of_year']= df_sorted['tanggal_dt'].dt.isocalendar().week.astype(int)
        
        df_sorted['bulan_sin']   = np.sin(2 * np.pi * df_sorted['bulan'] / 12)
        df_sorted['bulan_cos']   = np.cos(2 * np.pi * df_sorted['bulan'] / 12)
        df_sorted['dow_sin']     = np.sin(2 * np.pi * df_sorted['hari_pekan'] / 7)
        df_sorted['dow_cos']     = np.cos(2 * np.pi * df_sorted['hari_pekan'] / 7)
        
        df_sorted['is_peak_month'] = df_sorted['bulan'].isin([3, 4, 12]).astype(int)
        df_sorted['is_mid_year']   = df_sorted['bulan'].isin([6, 7]).astype(int)
        df_sorted['is_q4']         = (df_sorted['quarter'] == 4).astype(int)
        
        # 2. Log-transform Views
        for col in ['Facebook', 'Instagram', 'TikTok']:
            df_sorted[f'log_{col.lower()}'] = np.log1p(df_sorted[col])
            
        df_sorted['total_views']     = df_sorted['Facebook'] + df_sorted['Instagram'] + df_sorted['TikTok']
        df_sorted['log_total_views'] = np.log1p(df_sorted['total_views'])
        df_sorted['ratio_fb_total'] = df_sorted['Facebook']  / (df_sorted['total_views'] + 1)
        df_sorted['ratio_ig_total'] = df_sorted['Instagram'] / (df_sorted['total_views'] + 1)
        df_sorted['ratio_tt_total'] = df_sorted['TikTok']    / (df_sorted['total_views'] + 1)
        
        # 3. Growth Rate
        for col in ['Facebook', 'Instagram', 'TikTok', 'total_views']:
            prev = df_sorted[col].shift(1).replace(0, np.nan)
            df_sorted[f'{col.lower()}_growth'] = ((df_sorted[col] - df_sorted[col].shift(1)) / prev).fillna(0).clip(-2, 2)
            
        # 4. Lag Views
        for lag in [1, 3, 7]:
            df_sorted[f'fb_lag{lag}']  = df_sorted['Facebook'].shift(lag)
            df_sorted[f'ig_lag{lag}']  = df_sorted['Instagram'].shift(lag)
            df_sorted[f'tt_lag{lag}']  = df_sorted['TikTok'].shift(lag)
            
        # 5. Rolling Views
        df_sorted['views_roll7_mean']  = df_sorted['total_views'].shift(1).rolling(window=7,  min_periods=1).mean()
        df_sorted['views_roll14_mean'] = df_sorted['total_views'].shift(1).rolling(window=14, min_periods=1).mean()
        df_sorted['views_roll7_std']   = df_sorted['total_views'].shift(1).rolling(window=7,  min_periods=1).std().fillna(0)
        df_sorted['views_trend']  = df_sorted['views_roll7_mean']  - df_sorted['views_roll14_mean']
        
        # 6. Interaction
        df_sorted['log_views_x_weekend']   = df_sorted['log_total_views'] * df_sorted['is_weekend']
        df_sorted['log_views_x_peakmon']   = df_sorted['log_total_views'] * df_sorted['is_peak_month']
        df_sorted['log_views_x_q4']        = df_sorted['log_total_views'] * df_sorted['is_q4']
        
        from ml_indibiz.preprocessing import get_views_only_feature_columns
        cols = get_views_only_feature_columns()
        for c in cols:
            if c not in df_sorted.columns:
                df_sorted[c] = 0.0
                
        # Fill missing values to preserve row count (no dropna)
        df_sorted[cols] = df_sorted[cols].bfill().ffill().fillna(0.0)
        
        # Select features
        X_batch = df_sorted[cols].values
        
        # Scale and predict
        if views_only_scaler is not None and views_only_models:
            X_scaled = views_only_scaler.transform(X_batch)
            lr_preds = np.clip(views_only_models["Linear Regression"].predict(X_scaled), 0, 3)
            rf_preds = np.clip(views_only_models["Random Forest"].predict(X_scaled), 0, 3)
            xgb_preds = np.clip(views_only_models["XGBoost"].predict(X_scaled), 0, 3)
            avg_preds = (lr_preds + rf_preds + xgb_preds) / 3.0
            
            # Map predictions back
            df_sorted['lr_pred'] = lr_preds
            df_sorted['rf_pred'] = rf_preds
            df_sorted['xgb_pred'] = xgb_preds
            df_sorted['avg_pred'] = avg_preds
            
            # Sort back to original index
            df_res = df_sorted.sort_values('orig_index').reset_index(drop=True)
            
            classify = lambda val: 'Tinggi' if val >= 2 else 'Rendah'
            
            results = []
            for i in range(len(df_res)):
                row_res = {
                    "lr": {"value": float(df_res.loc[i, 'lr_pred']), "rounded": int(round(df_res.loc[i, 'lr_pred'])), "class": classify(df_res.loc[i, 'lr_pred'])},
                    "rf": {"value": float(df_res.loc[i, 'rf_pred']), "rounded": int(round(df_res.loc[i, 'rf_pred'])), "class": classify(df_res.loc[i, 'rf_pred'])},
                    "xgb": {"value": float(df_res.loc[i, 'xgb_pred']), "rounded": int(round(df_res.loc[i, 'xgb_pred'])), "class": classify(df_res.loc[i, 'xgb_pred'])},
                    "avg": float(df_res.loc[i, 'avg_pred']),
                    "tanggal": str(df_res.loc[i, 'tanggal']),
                    "Facebook": int(df_res.loc[i, 'Facebook']),
                    "Instagram": int(df_res.loc[i, 'Instagram']),
                    "TikTok": int(df_res.loc[i, 'TikTok']),
                    "id": int(df_res.loc[i, 'id'])
                }
                if 'Penjualan' in df_input.columns:
                    row_res["Penjualan"] = float(df_res.loc[i, 'Penjualan'])
                results.append(row_res)
                
            return jsonify({"success": True, "predictions": results})
        else:
            return jsonify({"error": "Model not loaded"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/model-metrics", methods=["GET"])
def model_metrics():
    if 'user' not in session or not is_authenticated():
        return jsonify({"error": "Unauthorized"}), 401
    try:
        results_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "results.json")
        with open(results_path, "r", encoding="utf-8") as f:
            metrics = json.load(f)
        return jsonify(metrics)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
