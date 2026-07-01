import sys, os, json, math, warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import TimeSeriesSplit, RandomizedSearchCV, cross_val_score
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor

DATA_PATH  = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard", "Data Harian.csv")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "figures")
os.makedirs(OUTPUT_DIR, exist_ok=True)

BULAN_ID = {"Jan":"01","Feb":"02","Mar":"03","Apr":"04","Mei":"05","Jun":"06",
            "Jul":"07","Agu":"08","Sep":"09","Okt":"10","Nov":"11","Des":"12"}

def banner(t): print(f"\n{'='*65}\n  {t}\n{'='*65}")

def load_data(path):
    df = pd.read_csv(path, usecols=range(6))
    df.columns = ["id","tanggal","Facebook","Instagram","TikTok","Penjualan"]
    for col in ["Facebook","Instagram","TikTok"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    def parse_tgl(s):
        s = str(s).strip()
        for k,v in BULAN_ID.items(): s = s.replace(k, v)
        try: return pd.to_datetime(s, format="%d %m %Y")
        except: return pd.NaT
    df["tanggal_dt"] = df["tanggal"].apply(parse_tgl)
    df = df.dropna(subset=["tanggal_dt"]).sort_values("tanggal_dt").reset_index(drop=True)
    df["total_views"] = df["Facebook"] + df["Instagram"] + df["TikTok"]
    return df

def feature_engineering(df):
    df = df.copy()
    df["hari"]        = df["tanggal_dt"].dt.day
    df["bulan"]       = df["tanggal_dt"].dt.month
    df["tahun"]       = df["tanggal_dt"].dt.year
    df["hari_pekan"]  = df["tanggal_dt"].dt.dayofweek
    df["is_weekend"]  = (df["hari_pekan"] >= 5).astype(int)
    df["quarter"]     = df["tanggal_dt"].dt.quarter
    df["week_of_year"]= df["tanggal_dt"].dt.isocalendar().week.astype(int)
    df["day_of_year"] = df["tanggal_dt"].dt.dayofyear
    df["bulan_sin"]   = np.sin(2*np.pi*df["bulan"]/12)
    df["bulan_cos"]   = np.cos(2*np.pi*df["bulan"]/12)
    df["dow_sin"]     = np.sin(2*np.pi*df["hari_pekan"]/7)
    df["dow_cos"]     = np.cos(2*np.pi*df["hari_pekan"]/7)
    df["doy_sin"]     = np.sin(2*np.pi*df["day_of_year"]/365)
    df["doy_cos"]     = np.cos(2*np.pi*df["day_of_year"]/365)
    df["is_peak_month"] = df["bulan"].isin([2,3,4,9,10,11]).astype(int)
    df["is_q4"]  = (df["quarter"] == 4).astype(int)
    df["is_jan"] = (df["bulan"] == 1).astype(int)

    for col in ["Facebook","Instagram","TikTok","total_views"]:
        df[f"log_{col.lower()}"] = np.log1p(df[col])

    df["ratio_fb"] = df["Facebook"]  / (df["total_views"] + 1)
    df["ratio_ig"] = df["Instagram"] / (df["total_views"] + 1)
    df["ratio_tt"] = df["TikTok"]    / (df["total_views"] + 1)

    for lag in [1,2,3,5,7,14,21,30]:
        df[f"tv_lag{lag}"] = df["total_views"].shift(lag)
    for lag in [1,3,7]:
        df[f"fb_lag{lag}"] = df["Facebook"].shift(lag)
        df[f"ig_lag{lag}"] = df["Instagram"].shift(lag)
        df[f"tt_lag{lag}"] = df["TikTok"].shift(lag)

    for w in [3,5,7,14,30]:
        df[f"tv_roll{w}_mean"] = df["total_views"].shift(1).rolling(w, min_periods=1).mean()
        df[f"tv_roll{w}_std"]  = df["total_views"].shift(1).rolling(w, min_periods=1).std().fillna(0)

    df["tv_trend_7_14"] = df["tv_roll7_mean"] - df["tv_roll14_mean"]
    df["tv_momentum"]   = df["tv_lag1"] - df["tv_lag2"]
    df = df.dropna().reset_index(drop=True)
    return df

FEATURES = [
    "tv_lag1","tv_lag2","tv_lag3","tv_lag5","tv_lag7","tv_lag14","tv_lag21","tv_lag30",
    "fb_lag1","fb_lag3","fb_lag7","ig_lag1","ig_lag3","ig_lag7","tt_lag1","tt_lag3","tt_lag7",
    "tv_roll3_mean","tv_roll5_mean","tv_roll7_mean","tv_roll14_mean","tv_roll30_mean",
    "tv_roll3_std","tv_roll5_std","tv_roll7_std",
    "tv_trend_7_14","tv_momentum","log_total_views",
    "hari","bulan","tahun","hari_pekan","is_weekend","quarter","week_of_year",
    "bulan_sin","bulan_cos","dow_sin","dow_cos","doy_sin","doy_cos",
    "is_peak_month","is_q4","is_jan","ratio_fb","ratio_ig","ratio_tt",
]

def main():
    banner("STEP 1: Load Data")
    df_raw = load_data(DATA_PATH)
    print(f"  Dataset: {len(df_raw)} baris")
    date_min = str(df_raw["tanggal_dt"].min().date())
    date_max = str(df_raw["tanggal_dt"].max().date())
    print(f"  Periode: {date_min} sd {date_max}")
    print(f"  Target : total_views = Facebook + Instagram + TikTok")

    banner("STEP 2: Feature Engineering")
    df = feature_engineering(df_raw)
    feat_cols = [c for c in FEATURES if c in df.columns]
    print(f"  Dataset FE: {len(df)} baris, {len(feat_cols)} fitur")

    banner("STEP 3: Split Data (80/20 time-based)")
    split_idx = int(len(df) * 0.8)
    X_all  = df[feat_cols].values
    y_all  = df["total_views"].values.astype(float)
    X_train, X_test = X_all[:split_idx], X_all[split_idx:]
    y_train, y_test = y_all[:split_idx], y_all[split_idx:]

    scaler = StandardScaler()
    X_tr = scaler.fit_transform(X_train)
    X_te = scaler.transform(X_test)
    print(f"  Train: {len(X_train)} | Test: {len(X_test)} | Fitur: {len(feat_cols)}")

    tscv = TimeSeriesSplit(n_splits=5)

    banner("STEP 4: Hyperparameter Tuning")

    print("  [Ridge]...")
    rs = RandomizedSearchCV(Ridge(),
        {"alpha": [0.001,0.01,0.1,1.0,10.0,100.0,500.0,1000.0]},
        n_iter=8, cv=tscv, scoring="r2", random_state=42, n_jobs=-1)
    rs.fit(X_tr, y_train)
    lr = rs.best_estimator_
    print(f"    best alpha={rs.best_params_['alpha']}  CV R2={rs.best_score_*100:.2f}%")

    print("  [Random Forest]...")
    rf_s = RandomizedSearchCV(
        RandomForestRegressor(random_state=42, n_jobs=-1),
        {"n_estimators":[300,500,700],"max_depth":[8,12,15,None],
         "min_samples_split":[2,3,5],"min_samples_leaf":[1,2],
         "max_features":["sqrt","log2",0.6,0.8]},
        n_iter=30, cv=tscv, scoring="r2", random_state=42, n_jobs=-1)
    rf_s.fit(X_tr, y_train)
    rf = rf_s.best_estimator_
    print(f"    CV R2={rf_s.best_score_*100:.2f}%")

    print("  [XGBoost]...")
    xgb_s = RandomizedSearchCV(
        XGBRegressor(random_state=42, n_jobs=-1, verbosity=0, tree_method="hist"),
        {"n_estimators":[300,500,700],"learning_rate":[0.01,0.02,0.05,0.1],
         "max_depth":[3,4,5,6],"subsample":[0.7,0.8,0.9],
         "colsample_bytree":[0.6,0.7,0.8,0.9],"min_child_weight":[1,2,3],
         "reg_alpha":[0,0.01,0.1],"reg_lambda":[0.5,1.0,1.5]},
        n_iter=40, cv=tscv, scoring="r2", random_state=42, n_jobs=-1)
    xgb_s.fit(X_tr, y_train)
    xgb = xgb_s.best_estimator_
    print(f"    CV R2={xgb_s.best_score_*100:.2f}%")

    banner("STEP 5: Evaluasi Test Set")
    results = {}
    print(f"\n  {'Model':<22} {'R2':>8} {'MAE':>10} {'RMSE':>10} {'MAPE':>8}")
    print(f"  {'-'*62}")
    for name, model in [("Linear Regression",lr),("Random Forest",rf),("XGBoost",xgb)]:
        yp   = model.predict(X_te)
        mae  = mean_absolute_error(y_test, yp)
        rmse = math.sqrt(mean_squared_error(y_test, yp))
        r2   = r2_score(y_test, yp)
        mape = float(np.mean(np.abs((y_test - yp) / y_test)) * 100)
        results[name] = {"MAE":round(mae,2),"RMSE":round(rmse,2),
                         "R2":round(r2,4),"R2_pct":round(r2*100,2),"MAPE":round(mape,2)}
        print(f"  {name:<22} {r2*100:>7.2f}% {mae:>10.1f} {rmse:>10.1f} {mape:>7.2f}%")

    banner("STEP 6: Cross-Validation")
    for name, model in [("Linear Regression",lr),("Random Forest",rf),("XGBoost",xgb)]:
        cv = cross_val_score(model, X_tr, y_train, cv=tscv, scoring="r2", n_jobs=-1)
        print(f"  {name:<22} CV R2={cv.mean()*100:.2f}% +/- {cv.std()*100:.2f}%")

    banner("STEP 7: Feature Importance")
    fi = sorted(zip(feat_cols, xgb.feature_importances_), key=lambda x: x[1], reverse=True)
    print("  Top 15 fitur (XGBoost):")
    for fname, fimp in fi[:15]:
        print(f"  {fname:<28} {fimp:.4f}")

    banner("STEP 8: Simpan JSON")
    correlation = {}
    for col in ["Facebook","Instagram","TikTok"]:
        try: correlation[col] = round(float(df[col].corr(df["total_views"])), 4)
        except: correlation[col] = 0.0

    try:
        mg = df.groupby("bulan").agg({"total_views":["sum","mean"],"Facebook":"mean","Instagram":"mean","TikTok":"mean"}).round(0)
        monthly = {}
        for b in mg.index:
            monthly[str(b)] = {
                "penjualan_sum":  float(mg.loc[b,("total_views","sum")]),
                "penjualan_mean": float(mg.loc[b,("total_views","mean")]),
                "facebook_mean":  float(mg.loc[b,("Facebook","mean")]),
                "instagram_mean": float(mg.loc[b,("Instagram","mean")]),
                "tiktok_mean":    float(mg.loc[b,("TikTok","mean")]),
            }
    except Exception as e:
        print(f"  Monthly error: {e}")
        monthly = {}

    feat_imp_dict = {"XGBoost": {f: round(float(imp),4) for f,imp in fi[:15]}}
    if hasattr(rf, "feature_importances_"):
        rf_fi = sorted(zip(feat_cols, rf.feature_importances_), key=lambda x: x[1], reverse=True)
        feat_imp_dict["Random Forest"] = {f: round(float(imp),4) for f,imp in rf_fi[:15]}

    best_name = max(results, key=lambda n: results[n]["R2"])
    full_results = {
        "regresi": results,
        "binary_classifier": {
            name: {"MAE":res["MAE"],"RMSE":res["RMSE"],
                   "R2":res["R2"],"R2_pct":res["R2_pct"],
                   "Accuracy":res["R2"],"Accuracy_bin":res["R2_pct"],"Accuracy_pct":res["R2_pct"]}
            for name, res in results.items()
        },
        "dataset_info": {
            "total_rows":  len(df_raw),
            "train_size":  len(X_train),
            "test_size":   len(X_test),
            "n_features":  len(feat_cols),
            "date_range":  f"{date_min} sd {date_max}",
            "platforms":   ["Facebook","Instagram","TikTok"],
            "target":      "Total Views (Facebook+Instagram+TikTok)",
            "best_model":  best_name,
        },
        "monthly_stats":    monthly,
        "correlation":      correlation,
        "feature_importance": feat_imp_dict,
    }

    out_path = os.path.join(OUTPUT_DIR, "results.json")
    with open(out_path, "w") as f:
        json.dump(full_results, f, indent=2, default=str)
    print(f"  JSON disimpan: {out_path}")

    banner("RINGKASAN AKHIR")
    print(f"\n  {'Model':<22} {'R2':>8}  {'MAE':>10}  {'RMSE':>10}")
    print(f"  {'-'*56}")
    for name, res in results.items():
        print(f"  {name:<22} {res['R2_pct']:>7.2f}%  {res['MAE']:>10.1f}  {res['RMSE']:>10.1f}")
    print(f"\n  Model terbaik : {best_name}")
    print(f"  R2 terbaik    : {results[best_name]['R2_pct']}%")

if __name__ == "__main__":
    main()

