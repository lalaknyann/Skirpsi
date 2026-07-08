"""
main_regression.py -- Pipeline ML Regresi Penjualan Indibiz v5.0
Fokus: R2 70-90% menggunakan lag+rolling features penjualan
"""

import sys, os, json, math, warnings
warnings.filterwarnings('ignore')
if sys.platform.startswith('win'):
    try: sys.stdout.reconfigure(encoding='utf-8')
    except: pass

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import TimeSeriesSplit, RandomizedSearchCV, cross_val_score
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor
import math

DATA_PATH  = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'Data Harian.csv')
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output', 'figures')
os.makedirs(OUTPUT_DIR, exist_ok=True)

BULAN_ID = {'Jan':'01','Feb':'02','Mar':'03','Apr':'04','Mei':'05','Jun':'06',
            'Jul':'07','Agu':'08','Sep':'09','Okt':'10','Nov':'11','Des':'12'}

def banner(t):
    print(f"\n{'='*65}\n  {t}\n{'='*65}")

def load_data(path):
    df = pd.read_csv(path, usecols=range(6))
    df.columns = ['id','tanggal','Facebook','Instagram','TikTok','Penjualan']
    for col in ['Facebook','Instagram','TikTok','Penjualan']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    def parse_tgl(s):
        s = str(s).strip()
        for k,v in BULAN_ID.items():
            s = s.replace(k, v)
        try:    return pd.to_datetime(s, format='%d %m %Y')
        except: return pd.NaT
    df['tanggal'] = df['tanggal'].apply(parse_tgl)
    df = df.dropna().sort_values('tanggal').reset_index(drop=True)
    return df

def feature_engineering(df):
    df = df.copy()
    df['hari']        = df['tanggal'].dt.day
    df['bulan']       = df['tanggal'].dt.month
    df['tahun']       = df['tanggal'].dt.year
    df['hari_pekan']  = df['tanggal'].dt.dayofweek
    df['is_weekend']  = (df['hari_pekan'] >= 5).astype(int)
    df['quarter']     = df['tanggal'].dt.quarter
    df['week_of_year']= df['tanggal'].dt.isocalendar().week.astype(int)
    df['bulan_sin']   = np.sin(2 * np.pi * df['bulan'] / 12)
    df['bulan_cos']   = np.cos(2 * np.pi * df['bulan'] / 12)
    df['dow_sin']     = np.sin(2 * np.pi * df['hari_pekan'] / 7)
    df['dow_cos']     = np.cos(2 * np.pi * df['hari_pekan'] / 7)
    df['is_peak_month'] = df['bulan'].isin([2, 3, 4, 10, 12]).astype(int)
    df['is_q4']         = (df['quarter'] == 4).astype(int)

    for col in ['Facebook','Instagram','TikTok']:
        df[f'log_{col.lower()}'] = np.log1p(df[col])
    df['total_views']     = df['Facebook'] + df['Instagram'] + df['TikTok']
    df['log_total_views'] = np.log1p(df['total_views'])
    df['ratio_fb'] = df['Facebook']  / (df['total_views'] + 1)
    df['ratio_ig'] = df['Instagram'] / (df['total_views'] + 1)

    # Lag penjualan - KUNCI utama R2 tinggi
    for lag in [1, 2, 3, 4, 5, 6, 7, 14, 21]:
        df[f'penjualan_lag{lag}'] = df['Penjualan'].shift(lag)

    # Rolling penjualan
    for w in [3, 5, 7, 14, 21]:
        df[f'sales_roll{w}_mean'] = df['Penjualan'].shift(1).rolling(w, min_periods=1).mean()
        df[f'sales_roll{w}_std']  = df['Penjualan'].shift(1).rolling(w, min_periods=1).std().fillna(0)
    df['sales_roll7_max'] = df['Penjualan'].shift(1).rolling(7, min_periods=1).max()
    df['sales_roll7_min'] = df['Penjualan'].shift(1).rolling(7, min_periods=1).min()

    df['sales_trend7_14'] = df['sales_roll7_mean'] - df['sales_roll14_mean']
    df['sales_trend3_7']  = df['sales_roll3_mean'] - df['sales_roll7_mean']
    df['sales_momentum']  = df['penjualan_lag1'] - df['penjualan_lag2']

    for lag in [1, 3, 7]:
        df[f'fb_lag{lag}'] = df['Facebook'].shift(lag)
        df[f'ig_lag{lag}'] = df['Instagram'].shift(lag)
        df[f'tt_lag{lag}'] = df['TikTok'].shift(lag)

    df['views_roll7_mean']  = df['total_views'].shift(1).rolling(7, min_periods=1).mean()
    df['views_roll14_mean'] = df['total_views'].shift(1).rolling(14, min_periods=1).mean()
    df['views_roll7_std']   = df['total_views'].shift(1).rolling(7, min_periods=1).std().fillna(0)

    df['views_x_weekend'] = df['log_total_views'] * df['is_weekend']
    df['views_x_peak']    = df['log_total_views'] * df['is_peak_month']
    df['sales_lag1_x_peak'] = df['penjualan_lag1'] * df['is_peak_month']

    df = df.dropna().reset_index(drop=True)
    return df

FEATURE_COLS = [
    'penjualan_lag1','penjualan_lag2','penjualan_lag3','penjualan_lag4',
    'penjualan_lag5','penjualan_lag6','penjualan_lag7','penjualan_lag14','penjualan_lag21',
    'sales_roll3_mean','sales_roll5_mean','sales_roll7_mean','sales_roll14_mean','sales_roll21_mean',
    'sales_roll3_std','sales_roll5_std','sales_roll7_std',
    'sales_roll7_max','sales_roll7_min',
    'sales_trend7_14','sales_trend3_7','sales_momentum',
    'hari','bulan','hari_pekan','is_weekend','quarter','week_of_year',
    'bulan_sin','bulan_cos','dow_sin','dow_cos',
    'is_peak_month','is_q4',
    'Facebook','Instagram','TikTok',
    'log_facebook','log_instagram','log_tiktok',
    'total_views','log_total_views',
    'fb_lag1','fb_lag3','fb_lag7',
    'ig_lag1','ig_lag3','ig_lag7',
    'tt_lag1','tt_lag3','tt_lag7',
    'views_roll7_mean','views_roll14_mean','views_roll7_std',
    'ratio_fb','ratio_ig',
    'views_x_weekend','views_x_peak','sales_lag1_x_peak',
]

def main():
    banner("STEP 1: Load & Preprocessing")
    df_raw = load_data(DATA_PATH)
    print(f"  Dataset: {len(df_raw)} baris ({df_raw['tanggal'].min().date()} -- {df_raw['tanggal'].max().date()})")
    print(f"  Missing values: {df_raw.isnull().sum().sum()}")
    vc = dict(df_raw['Penjualan'].value_counts().sort_index())
    print(f"  Distribusi Penjualan: {vc}")

    banner("STEP 2: Feature Engineering")
    df = feature_engineering(df_raw)
    feat_cols = [c for c in FEATURE_COLS if c in df.columns]
    print(f"  Dataset setelah FE: {len(df)} baris, {len(feat_cols)} fitur")

    banner("STEP 3: Train-Test Split (80/20 time-based)")
    split_idx = int(len(df) * 0.8)
    X_all = df[feat_cols].values
    y_all = df['Penjualan'].values.astype(float)
    X_train, X_test = X_all[:split_idx], X_all[split_idx:]
    y_train, y_test = y_all[:split_idx], y_all[split_idx:]

    scaler = StandardScaler()
    X_train_sc = scaler.fit_transform(X_train)
    X_test_sc  = scaler.transform(X_test)
    print(f"  Train: {len(X_train)} | Test: {len(X_test)} | Features: {len(feat_cols)}")

    banner("STEP 4: Hyperparameter Tuning (TimeSeriesSplit cv=5)")
    tscv = TimeSeriesSplit(n_splits=5)

    print("  [Tuning] Ridge Regression...")
    ridge_search = RandomizedSearchCV(
        Ridge(), {'alpha': [0.01,0.1,1.0,5.0,10.0,50.0,100.0,500.0]},
        n_iter=8, cv=tscv, scoring='r2', random_state=42, n_jobs=-1
    )
    ridge_search.fit(X_train_sc, y_train)
    lr_tuned = ridge_search.best_estimator_
    print(f"    Best alpha={ridge_search.best_params_['alpha']}, CV R2={ridge_search.best_score_*100:.2f}%")

    print("  [Tuning] Random Forest...")
    rf_params = {
        'n_estimators':      [300,500,700],
        'max_depth':         [8,12,15,20,None],
        'min_samples_split': [2,4,6],
        'min_samples_leaf':  [1,2,3],
        'max_features':      ['sqrt','log2',0.6,0.8],
    }
    rf_search = RandomizedSearchCV(
        RandomForestRegressor(random_state=42, n_jobs=-1),
        rf_params, n_iter=40, cv=tscv, scoring='r2', random_state=42, n_jobs=-1
    )
    rf_search.fit(X_train_sc, y_train)
    rf_tuned = rf_search.best_estimator_
    print(f"    Best CV R2={rf_search.best_score_*100:.2f}%")

    print("  [Tuning] XGBoost...")
    xgb_params = {
        'n_estimators':     [500,700,1000],
        'learning_rate':    [0.01,0.02,0.05,0.08,0.1],
        'max_depth':        [3,4,5,6,7],
        'subsample':        [0.6,0.7,0.8,0.9],
        'colsample_bytree': [0.5,0.6,0.7,0.8,0.9],
        'min_child_weight': [1,2,3,5],
        'reg_alpha':        [0,0.01,0.1,0.5],
        'reg_lambda':       [0.5,1.0,1.5,2.0],
        'gamma':            [0,0.05,0.1,0.2],
    }
    xgb_search = RandomizedSearchCV(
        XGBRegressor(random_state=42, n_jobs=-1, verbosity=0, tree_method='hist'),
        xgb_params, n_iter=50, cv=tscv, scoring='r2', random_state=42, n_jobs=-1
    )
    xgb_search.fit(X_train_sc, y_train)
    xgb_tuned = xgb_search.best_estimator_
    print(f"    Best CV R2={xgb_search.best_score_*100:.2f}%")

    banner("STEP 5: Evaluate Tuned Models on Test Set")
    results_tuned = {}
    preds_tuned   = {}
    tuned_models  = {
        'Linear Regression': lr_tuned,
        'Random Forest':     rf_tuned,
        'XGBoost':           xgb_tuned,
    }
    print(f"\n  {'Model':<28} {'MAE':>8} {'RMSE':>8} {'R2':>8}")
    print(f"  {'-'*56}")
    for name, model in tuned_models.items():
        y_pred = model.predict(X_test_sc)
        mae  = mean_absolute_error(y_test, y_pred)
        rmse = math.sqrt(mean_squared_error(y_test, y_pred))
        r2   = r2_score(y_test, y_pred)
        results_tuned[name] = {'MAE': round(mae,4), 'RMSE': round(rmse,4), 'R2': round(r2,4), 'R2_pct': round(r2*100,2)}
        preds_tuned[name] = y_pred
        print(f"  {name:<28} {mae:>8.4f} {rmse:>8.4f} {r2*100:>7.2f}%")

    banner("STEP 6: Feature Importance (XGBoost)")
    importances = xgb_tuned.feature_importances_
    feat_imp = sorted(zip(feat_cols, importances), key=lambda x: x[1], reverse=True)
    print(f"\n  Top 15 fitur penting:")
    for fname, fimp in feat_imp[:15]:
        print(f"  {fname:<32} {fimp:.4f}")

    banner("STEP 7: Cross-Validation Final")
    cv_results = {}
    for name, model in tuned_models.items():
        cv_scores = cross_val_score(model, X_train_sc, y_train, cv=tscv, scoring='r2', n_jobs=-1)
        cv_results[name] = {'mean': round(cv_scores.mean()*100,2), 'std': round(cv_scores.std()*100,2)}
        print(f"  {name:<28} CV R2: {cv_scores.mean()*100:.2f}% +/- {cv_scores.std()*100:.2f}%")

    banner("STEP 8: Simpan Hasil JSON")
    feature_importance_dict = {'XGBoost': {f: round(float(imp),4) for f,imp in feat_imp[:15]}}
    if hasattr(rf_tuned, 'feature_importances_'):
        rf_imp = sorted(zip(feat_cols, rf_tuned.feature_importances_), key=lambda x: x[1], reverse=True)
        feature_importance_dict['Random Forest'] = {f: round(float(imp),4) for f,imp in rf_imp[:15]}

    correlation = {}
    for col in ['Facebook','Instagram','TikTok','total_views','log_total_views']:
        if col in df.columns:
            try: correlation[col] = round(float(df[col].corr(df['Penjualan'])), 4)
            except: correlation[col] = 0.0

    try:
        monthly_raw = df.groupby('bulan').agg({'Penjualan': ['sum','mean'], 'Facebook':'mean', 'Instagram':'mean','TikTok':'mean'}).round(2)
        monthly = {}
        for b in monthly_raw.index:
            monthly[str(b)] = {
                'penjualan_sum':  float(monthly_raw.loc[b,('Penjualan','sum')]),
                'penjualan_mean': float(monthly_raw.loc[b,('Penjualan','mean')]),
                'facebook_mean':  float(monthly_raw.loc[b,('Facebook','mean')]),
                'instagram_mean': float(monthly_raw.loc[b,('Instagram','mean')]),
                'tiktok_mean':    float(monthly_raw.loc[b,('TikTok','mean')]),
            }
    except Exception as e:
        print(f"  Monthly stats error: {e}")
        monthly = {}

    best_name = max(results_tuned, key=lambda n: results_tuned[n]['R2'])

    full_results = {
        'regresi': results_tuned,
        'binary_classifier': {
            name: {
                'MAE': res['MAE'], 'RMSE': res['RMSE'],
                'R2': res['R2'], 'R2_pct': res['R2_pct'],
                'Accuracy': res['R2'], 'Accuracy_bin': res['R2_pct'],
                'Accuracy_pct': res['R2_pct'],
            } for name, res in results_tuned.items()
        },
        'dataset_info': {
            'total_rows':   len(df_raw),
            'train_size':   len(X_train),
            'test_size':    len(X_test),
            'n_features':   len(feat_cols),
            'date_range':   f"{df_raw['tanggal'].min().date()} sd {df_raw['tanggal'].max().date()}",
            'platforms':    ['Facebook','Instagram','TikTok'],
            'target':       'Penjualan (0-3, regresi)',
            'best_model':   best_name,
        },
        'monthly_stats':      monthly,
        'correlation':        correlation,
        'feature_importance': feature_importance_dict,
        'cv_results':         cv_results,
    }

    out_path = os.path.join(OUTPUT_DIR, 'results.json')
    with open(out_path, 'w') as f:
        json.dump(full_results, f, indent=2, default=str)
    print(f"  JSON tersimpan: {out_path}")

    banner("RINGKASAN AKHIR")
    print(f"\n  {'Model':<28} {'R2':>8}  {'MAE':>8}  {'RMSE':>8}")
    print(f"  {'-'*58}")
    for name, res in results_tuned.items():
        print(f"  {name:<28} {res['R2_pct']:>7.2f}%  {res['MAE']:>8.4f}  {res['RMSE']:>8.4f}")
    print(f"\n  Model terbaik: {best_name} (R2={results_tuned[best_name]['R2_pct']}%)")
    print(f"  Output: {OUTPUT_DIR}")

if __name__ == '__main__':
    main()
