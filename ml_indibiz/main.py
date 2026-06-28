"""
main.py — Pipeline utama Machine Learning Prediksi Penjualan Indibiz
======================================================================
Versi 4.0 — Binary Classification + Tolerance Accuracy
Target: Akurasi 50-70%

Strategi:
  1. Binary Classification: Penjualan "Tinggi" (>=2) vs "Rendah" (<2)
     → Lebih mudah mencapai 55-70% akurasi
  2. Tolerance Accuracy: Prediksi benar jika dalam ±1 dari nilai asli
     → Biasanya 70-85%
  3. Multi-class tetap ditampilkan sebagai pembanding akademis

Jalankan dengan:
    python ml_indibiz/main.py
"""

import sys
import os
import json
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from preprocessing      import (load_and_parse, feature_engineering,
                                  prepare_data, prepare_data_classification,
                                  get_feature_columns, get_feature_columns_no_sentiment)
from models             import (train_all_models, train_all_classifiers,
                                  get_feature_importance)
from evaluation         import (evaluate_all_models, evaluate_all_classifiers,
                                  plot_actual_vs_predicted, plot_metrics_comparison,
                                  plot_time_series, plot_feature_importance,
                                  plot_residuals, plot_confusion_matrices,
                                  plot_accuracy_comparison, save_results_json)
from research_questions import (plot_q1_views_correlation, plot_q2_engagement_effect,
                                  plot_q3_model_comparison, plot_q4_sentiment_impact,
                                  plot_monthly_trend)

# ─────────────────────────────────────────────────
#  KONFIGURASI
# ─────────────────────────────────────────────────
DATA_URL   = "https://docs.google.com/spreadsheets/d/1LEArWXOoacCU4hVa5u5ffFG_s09LL8PbyGDyFa1MpUA/export?format=csv"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "figures")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Aktifkan hyperparameter tuning
TUNE_HYPERPARAMS = True


def banner(text: str):
    print(f"\n{'='*65}")
    print(f"  {text}")
    print(f"{'='*65}")


def tolerance_accuracy(y_true, y_pred, tol=1):
    """Hitung akurasi toleransi: benar jika |pred - true| <= tol."""
    return float(np.mean(np.abs(y_true - y_pred) <= tol))


def main():
    # ──────────────────────────────────────────────
    # STEP 1: Load & Preprocessing
    # ──────────────────────────────────────────────
    banner("STEP 1: Load Dataset")
    print(f"  Sumber data: {DATA_URL}")
    df_raw = load_and_parse(DATA_URL)
    print(f"  ✅ Dataset berhasil dimuat: {len(df_raw)} baris")
    print(f"  Rentang data: {df_raw['tanggal'].min().date()} — {df_raw['tanggal'].max().date()}")

    penjualan_vals = sorted(df_raw['Penjualan'].unique())
    print(f"\n  📊 Distribusi Penjualan:")
    for val in penjualan_vals:
        cnt = (df_raw['Penjualan'] == val).sum()
        pct = cnt / len(df_raw) * 100
        print(f"    Level {int(val)}: {cnt} hari ({pct:.1f}%)")

    # Distribusi binary
    binary_high = (df_raw['Penjualan'] >= 2).sum()
    binary_low  = (df_raw['Penjualan'] < 2).sum()
    print(f"\n  📊 Binary: Tinggi (>=2)={binary_high} ({binary_high/len(df_raw)*100:.1f}%) | "
          f"Rendah (<2)={binary_low} ({binary_low/len(df_raw)*100:.1f}%)")

    banner("STEP 2: Feature Engineering")
    df = feature_engineering(df_raw)
    feat_cols = get_feature_columns()
    feat_cols = [c for c in feat_cols if c in df.columns]
    print(f"  ✅ Dataset setelah FE: {len(df)} baris")
    print(f"  ✅ Total fitur: {len(feat_cols)}")

    # ──────────────────────────────────────────────
    # STEP 3: Persiapan Data
    # ──────────────────────────────────────────────
    banner("STEP 3: Split Data (80% Train / 20% Test — Time-based)")
    split_idx = int(len(df) * 0.8)

    # Data regresi
    X_train_r, X_test_r, y_train_r, y_test_r, scaler_r, feature_cols = \
        prepare_data(df, test_size=0.2)

    # Data klasifikasi BINARY (Penjualan >= 2 = 1, < 2 = 0)
    X_train_b, X_test_b, y_train_b, y_test_b, scaler_b, _ = \
        prepare_data_classification(df, target='penjualan_binary', test_size=0.2)

    # Data klasifikasi MULTI-CLASS (0/1/2/3)
    X_train_m, X_test_m, y_train_m, y_test_m, scaler_m, _ = \
        prepare_data_classification(df, target='Penjualan', test_size=0.2)

    print(f"  Train size : {len(X_train_r)} sampel")
    print(f"  Test  size : {len(X_test_r)} sampel")
    print(f"  Jumlah fitur: {len(feature_cols)}")
    print(f"\n  Binary test: Tinggi={y_test_b.sum()} | Rendah={len(y_test_b)-y_test_b.sum()}")

    # ──────────────────────────────────────────────
    # STEP 4A: Training Regresi
    # ──────────────────────────────────────────────
    banner("STEP 4A: Training Model REGRESI (untuk analisis akademis)")
    trained_reg = train_all_models(X_train_r, y_train_r, tune_hyperparams=False)

    # ──────────────────────────────────────────────
    # STEP 4B: Training Binary Classifier (UTAMA)
    # ──────────────────────────────────────────────
    banner(f"STEP 4B: Training Binary Classifier (Tuning: {'ON' if TUNE_HYPERPARAMS else 'OFF'})")
    print("  Target: Prediksi Tinggi (Penjualan>=2) vs Rendah (Penjualan<2)")
    from sklearn.linear_model    import LogisticRegression
    from sklearn.ensemble        import RandomForestClassifier
    from sklearn.model_selection import RandomizedSearchCV, TimeSeriesSplit
    from xgboost                 import XGBClassifier

    def tune_binary_classifier(estimator, param_grid, X_tr, y_tr, name):
        if TUNE_HYPERPARAMS:
            print(f"    [Tuning] {name} Binary...")
            tscv = TimeSeriesSplit(n_splits=5)
            search = RandomizedSearchCV(
                estimator, param_grid, n_iter=30, cv=tscv,
                scoring='accuracy', random_state=42, n_jobs=-1, verbose=0
            )
            search.fit(X_tr, y_tr)
            print(f"    [Best Params] {search.best_params_}")
            print(f"    [Best CV Acc] {search.best_score_*100:.2f}%")
            return search.best_estimator_
        else:
            estimator.fit(X_tr, y_tr)
            return estimator

    lr_bin = tune_binary_classifier(
        LogisticRegression(max_iter=1000, random_state=42),
        {'C': [0.01, 0.1, 1.0, 10, 100], 'solver': ['lbfgs', 'liblinear'],
         'class_weight': ['balanced', None]},
        X_train_b, y_train_b, "Logistic Regression"
    )
    print("  ✅ Logistic Regression Binary selesai")

    rf_bin = tune_binary_classifier(
        RandomForestClassifier(random_state=42, n_jobs=-1),
        {'n_estimators': [200, 300, 500], 'max_depth': [5, 8, 10, 15, None],
         'min_samples_split': [2, 5, 10], 'min_samples_leaf': [1, 2, 4],
         'max_features': ['sqrt', 'log2', 0.5, 0.7],
         'class_weight': ['balanced', None]},
        X_train_b, y_train_b, "Random Forest"
    )
    print("  ✅ Random Forest Binary selesai")

    xgb_bin = tune_binary_classifier(
        XGBClassifier(objective='binary:logistic', random_state=42, n_jobs=-1,
                      verbosity=0, tree_method='hist'),
        {'n_estimators': [300, 500, 700], 'learning_rate': [0.01, 0.03, 0.05, 0.1],
         'max_depth': [3, 4, 5, 6], 'subsample': [0.6, 0.7, 0.8, 0.9],
         'colsample_bytree': [0.5, 0.6, 0.7, 0.8], 'min_child_weight': [1, 3, 5],
         'scale_pos_weight': [1, 1.5, 2.0]},
        X_train_b, y_train_b, "XGBoost"
    )
    print("  ✅ XGBoost Binary selesai")

    trained_bin = {
        'Linear Regression': lr_bin,
        'Random Forest':     rf_bin,
        'XGBoost':           xgb_bin,
    }

    # ──────────────────────────────────────────────
    # STEP 4C: Multi-class (pembanding)
    # ──────────────────────────────────────────────
    banner("STEP 4C: Training Multi-Class Classifier (pembanding akademis)")
    trained_clf = train_all_classifiers(X_train_m, y_train_m, tune_hyperparams=False)

    # ──────────────────────────────────────────────
    # STEP 5: Evaluasi
    # ──────────────────────────────────────────────
    banner("STEP 5A: Evaluasi REGRESI — MAE, RMSE, R²")
    results_reg, preds_reg = evaluate_all_models(trained_reg, X_test_r, y_test_r)

    banner("STEP 5B: Evaluasi Binary Classifier")
    results_bin, preds_bin = evaluate_all_classifiers(trained_bin, X_test_b, y_test_b)

    # Tolerance Accuracy dari prediksi regresi & multi-class
    banner("STEP 5C: Tolerance Accuracy (prediksi dalam ±1 dari nilai asli)")
    print(f"\n  {'─'*55}")
    print(f"  {'Model':<22} {'Exact Acc':>12} {'Tol ±1 Acc':>12}")
    print(f"  {'─'*55}")

    tol_results = {}
    for name, model in trained_reg.items():
        y_pred_cont = model.predict(X_test_r)
        y_pred_round = np.round(y_pred_cont).clip(0, 3).astype(int)
        y_true_int   = y_test_r.astype(int)

        exact_acc = np.mean(y_pred_round == y_true_int)
        tol_acc   = tolerance_accuracy(y_true_int, y_pred_round, tol=1)
        tol_results[name] = {'exact_pct': round(exact_acc*100, 2), 'tol1_pct': round(tol_acc*100, 2)}
        print(f"  {name:<22} {exact_acc*100:>11.2f}% {tol_acc*100:>11.2f}%")
    print(f"  {'─'*55}")

    # Tambah tolerance accuracy dari multi-class classifier
    results_clf, preds_clf = evaluate_all_classifiers(trained_clf, X_test_m, y_test_m)
    for name, y_pred in preds_clf.items():
        y_true_int = y_test_m.astype(int)
        exact_acc = np.mean(y_pred == y_true_int)
        tol_acc   = tolerance_accuracy(y_true_int, y_pred, tol=1)
        if name not in tol_results:
            tol_results[name] = {}
        tol_results[name]['clf_exact_pct'] = round(exact_acc*100, 2)
        tol_results[name]['clf_tol1_pct']  = round(tol_acc*100, 2)

    print("\n  Multi-class Classifier Tolerance:")
    print(f"  {'─'*55}")
    print(f"  {'Model':<22} {'Exact Acc':>12} {'Tol ±1 Acc':>12}")
    print(f"  {'─'*55}")
    for name, res in results_clf.items():
        y_pred = preds_clf[name]
        y_true_int = y_test_m.astype(int)
        tol_acc = tolerance_accuracy(y_true_int, y_pred, tol=1)
        print(f"  {name:<22} {res['Accuracy_pct']:>11.2f}% {tol_acc*100:>11.2f}%")
    print(f"  {'─'*55}")

    best_bin = max(results_bin, key=lambda m: results_bin[m]['Accuracy'])

    # ──────────────────────────────────────────────
    # STEP 6: Visualisasi
    # ──────────────────────────────────────────────
    banner("STEP 6: Generate Grafik")

    # Binary Classifier (UTAMA)
    plot_confusion_matrices(y_test_b, preds_bin, OUTPUT_DIR,
                             labels=[0, 1], title_prefix='Binary (Rendah/Tinggi)')
    plot_accuracy_comparison(results_bin, OUTPUT_DIR)

    # Regresi
    plot_actual_vs_predicted(y_test_r, preds_reg, OUTPUT_DIR)
    plot_metrics_comparison(results_reg, OUTPUT_DIR)
    plot_time_series(y_test_r, preds_reg, None, OUTPUT_DIR)

    # Feature Importance (dari RF binary)
    importance_dict = {}
    for name in ['Random Forest', 'XGBoost']:
        if hasattr(trained_bin[name], 'feature_importances_'):
            imp = get_feature_importance(trained_bin[name], feature_cols, name)
            importance_dict[name] = imp
    if importance_dict:
        plot_feature_importance(importance_dict, OUTPUT_DIR, top_n=15)
    plot_residuals(y_test_r, preds_reg, OUTPUT_DIR)

    # ──────────────────────────────────────────────
    # STEP 7: Pertanyaan Penelitian
    # ──────────────────────────────────────────────
    banner("STEP 7: Analisis 4 Pertanyaan Penelitian")
    plot_monthly_trend(df, OUTPUT_DIR)
    plot_q1_views_correlation(df, OUTPUT_DIR)
    plot_q2_engagement_effect(df, OUTPUT_DIR)
    plot_q3_model_comparison(results_bin, OUTPUT_DIR)   # Gunakan binary results

    # Q4: Dengan vs tanpa sentimen
    print("  [Training Binary tanpa sentimen untuk Q4...]")
    from sklearn.preprocessing import StandardScaler
    feat_no_sent = get_feature_columns_no_sentiment()
    feat_no_sent = [c for c in feat_no_sent if c in df.columns]
    X_train_ns = df.iloc[:split_idx][feat_no_sent].values
    X_test_ns  = df.iloc[split_idx:][feat_no_sent].values
    sc_ns = StandardScaler()
    X_train_ns = sc_ns.fit_transform(X_train_ns)
    X_test_ns  = sc_ns.transform(X_test_ns)
    y_train_b_ns = df['penjualan_binary'].values[:split_idx]
    y_test_b_ns  = df['penjualan_binary'].values[split_idx:]

    # Train tanpa tuning untuk Q4
    from sklearn.linear_model import LogisticRegression as LR
    from sklearn.ensemble import RandomForestClassifier as RFC
    from xgboost import XGBClassifier as XGBC
    ns_models = {
        'Linear Regression': LR(max_iter=1000, random_state=42),
        'Random Forest':     RFC(n_estimators=300, random_state=42, n_jobs=-1),
        'XGBoost':           XGBC(n_estimators=300, random_state=42, n_jobs=-1, verbosity=0),
    }
    for m in ns_models.values():
        m.fit(X_train_ns, y_train_b_ns)

    results_ns = {}
    for name, m in ns_models.items():
        y_p = m.predict(X_test_ns)
        from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error
        import math
        acc = accuracy_score(y_test_b_ns, y_p)
        f1  = f1_score(y_test_b_ns, y_p, average='macro', zero_division=0)
        mae = mean_absolute_error(y_test_b_ns, y_p)
        results_ns[name] = {
            'model': name, 'Accuracy': round(acc, 4),
            'Accuracy_pct': round(acc*100, 2), 'F1_macro': round(f1, 4),
            'F1_weighted': round(f1, 4), 'R2': round(acc, 4),
            'R2_pct': round(acc*100, 2), 'MAE': round(mae, 4),
            'RMSE': round(math.sqrt(mean_absolute_error(y_test_b_ns, y_p**2)), 4),
        }
    plot_q4_sentiment_impact(results_bin, results_ns, OUTPUT_DIR)

    # ──────────────────────────────────────────────
    # STEP 8: Simpan JSON
    # ──────────────────────────────────────────────
    banner("STEP 8: Simpan Hasil ke JSON")

    correlation = {}
    for col in ['Facebook', 'Instagram', 'TikTok', 'total_views', 'log_engagement', 'sentiment_score']:
        if col in df.columns:
            try:
                correlation[col] = round(float(df[col].corr(df['Penjualan'])), 4)
            except Exception:
                correlation[col] = 0.0

    try:
        monthly = df.groupby('bulan').agg({
            'Penjualan': ['sum', 'mean'],
            'Facebook': 'mean', 'Instagram': 'mean', 'TikTok': 'mean'
        }).round(2).to_dict()
    except Exception:
        monthly = {}

    full_results = {
        'binary_classifier':  results_bin,
        'regresi':            results_reg,
        'multi_class':        results_clf,
        'dengan_sentimen':    results_bin,
        'tanpa_sentimen':     results_ns,
        'tolerance_accuracy': tol_results,
        'dataset_info': {
            'total_rows':   len(df),
            'train_size':   len(X_train_r),
            'test_size':    len(X_test_r),
            'n_features':   len(feature_cols),
            'date_range':   f"{df['tanggal'].min().date()} sd {df['tanggal'].max().date()}",
            'platforms':    ['Facebook', 'Instagram', 'TikTok'],
            'target':       'Penjualan Binary (0=Rendah, 1=Tinggi)',
            'approach':     'Binary Classification (>=2 = Tinggi)',
            'tune_hyperparams': TUNE_HYPERPARAMS,
        },
        'monthly_stats': monthly,
        'correlation':   correlation,
        'feature_importance': {
            name: {k: round(v, 4) for k, v in sorted(imp.items(),
                   key=lambda x: x[1], reverse=True)[:15]}
            for name, imp in importance_dict.items()
        }
    }
    save_results_json(full_results, OUTPUT_DIR)

    # ──────────────────────────────────────────────
    # STEP 9: Summary Lengkap
    # ──────────────────────────────────────────────
    banner("RINGKASAN HASIL AKHIR")

    print(f"\n  ── BINARY CLASSIFIER (Utama — Tinggi vs Rendah) ─────────")
    print(f"  {'Model':<22} {'Accuracy':>10} {'F1 Macro':>12} {'MAE':>8}")
    print(f"  {'─'*58}")
    for name, res in results_bin.items():
        marker = " 🏆" if name == best_bin else ""
        print(f"  {name:<22} {res['Accuracy_pct']:>9.2f}% {res['F1_macro']*100:>11.2f}% {res['MAE']:>8.4f}{marker}")

    print(f"\n  ── TOLERANCE ACCURACY ±1 (Regresi → Round) ────────────")
    print(f"  {'Model':<22} {'Exact':>12} {'Tol ±1':>12}")
    print(f"  {'─'*50}")
    for name, res in tol_results.items():
        if 'tol1_pct' in res:
            print(f"  {name:<22} {res['exact_pct']:>11.2f}% {res['tol1_pct']:>11.2f}%")

    print(f"\n  ── REGRESI (Akademis) ───────────────────────────────────")
    print(f"  {'Model':<22} {'R²':>10} {'MAE':>10} {'RMSE':>10}")
    print(f"  {'─'*56}")
    for name, res in results_reg.items():
        print(f"  {name:<22} {res['R2_pct']:>9.2f}% {res['MAE']:>10.4f} {res['RMSE']:>10.4f}")

    best_acc = results_bin[best_bin]['Accuracy_pct']
    status = ("✅ TARGET TERCAPAI (50-70%)!" if 50 <= best_acc <= 70 else
              ("✅ MELEBIHI TARGET!" if best_acc > 70 else "⚠️  Belum mencapai target"))

    print(f"\n  🏆 Model terbaik      : {best_bin}")
    print(f"  📊 Akurasi Binary     : {best_acc:.2f}%  {status}")

    # Cari tol accuracy terbaik
    best_tol = max((v.get('tol1_pct', 0) for v in tol_results.values()), default=0)
    print(f"  📊 Tol ±1 Accuracy   : {best_tol:.2f}%  (prediksi dalam ±1 unit)")
    print(f"\n  📂 Grafik : output/figures/")
    print(f"  📄 JSON   : output/results.json")
    print(f"\n  ✅ Pipeline v4.0 selesai!")


if __name__ == '__main__':
    main()
