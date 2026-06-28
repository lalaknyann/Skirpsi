"""
models.py
Definisi dan training model ML: Regression + Classification
Versi 3.0 — Dual approach untuk mencapai akurasi 50-70%

Insight penting:
  Penjualan (0-3) adalah variabel DISKRET → cocok untuk KLASIFIKASI.
  Untuk regresi, digunakan sebagai perbandingan akademis.
"""

import numpy as np
import warnings
warnings.filterwarnings('ignore')

from sklearn.linear_model    import Ridge, LogisticRegression
from sklearn.ensemble        import RandomForestRegressor, RandomForestClassifier
from sklearn.model_selection import RandomizedSearchCV, TimeSeriesSplit
from xgboost                 import XGBRegressor, XGBClassifier


# ───────────────────────────────────────────────
#  REGRESI (untuk analisis akademis R²)
# ───────────────────────────────────────────────

def build_linear_regression():
    """Ridge Regression — stabil, cegah overfitting."""
    return Ridge(alpha=10.0, fit_intercept=True)


def build_random_forest_regressor():
    """Random Forest Regressor — preset optimal."""
    return RandomForestRegressor(
        n_estimators=500, max_depth=10,
        min_samples_split=5, min_samples_leaf=2,
        max_features='sqrt', random_state=42, n_jobs=-1
    )


def build_xgboost_regressor():
    """XGBoost Regressor — preset optimal."""
    return XGBRegressor(
        n_estimators=500, learning_rate=0.05,
        max_depth=5, subsample=0.8,
        colsample_bytree=0.7, reg_alpha=0.1,
        reg_lambda=1.0, random_state=42,
        n_jobs=-1, verbosity=0, tree_method='hist'
    )


def train_all_models(X_train, y_train, tune_hyperparams=False):
    """Training semua model REGRESI."""
    lr = build_linear_regression()
    lr.fit(X_train, y_train)
    print("  ✅ Linear Regression (Ridge) selesai")

    rf = build_random_forest_regressor()
    rf.fit(X_train, y_train)
    print("  ✅ Random Forest Regressor selesai")

    xgb = build_xgboost_regressor()
    xgb.fit(X_train, y_train)
    print("  ✅ XGBoost Regressor selesai")

    return {
        'Linear Regression': lr,
        'Random Forest':     rf,
        'XGBoost':           xgb,
    }


# ───────────────────────────────────────────────
#  KLASIFIKASI (target utama akurasi 50-70%)
# ───────────────────────────────────────────────

def build_logistic_regression_clf():
    """Logistic Regression multi-class."""
    return LogisticRegression(
        multi_class='multinomial', solver='lbfgs',
        C=1.0, max_iter=1000, random_state=42
    )


def build_random_forest_clf(tune=True, X_train=None, y_train=None):
    """
    Random Forest Classifier.
    Jika tune=True, jalankan RandomizedSearchCV.
    """
    if tune and X_train is not None and y_train is not None:
        print("    [Tuning] Random Forest Classifier via RandomizedSearchCV...")
        param_grid = {
            'n_estimators':      [200, 300, 500],
            'max_depth':         [5, 8, 10, 15, None],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf':  [1, 2, 4],
            'max_features':      ['sqrt', 'log2', 0.5],
            'class_weight':      ['balanced', None],
        }
        tscv = TimeSeriesSplit(n_splits=5)
        base = RandomForestClassifier(random_state=42, n_jobs=-1)
        search = RandomizedSearchCV(
            base, param_grid, n_iter=40, cv=tscv,
            scoring='accuracy', random_state=42, n_jobs=-1, verbose=0
        )
        search.fit(X_train, y_train)
        print(f"    [Best RF Params]    {search.best_params_}")
        print(f"    [Best RF CV Acc]    {search.best_score_:.4f} ({search.best_score_*100:.2f}%)")
        return search.best_estimator_
    else:
        return RandomForestClassifier(
            n_estimators=500, max_depth=10,
            min_samples_split=2, min_samples_leaf=1,
            max_features='sqrt', class_weight='balanced',
            random_state=42, n_jobs=-1
        )


def build_xgboost_clf(tune=True, X_train=None, y_train=None, n_classes=4):
    """
    XGBoost Classifier.
    Jika tune=True, jalankan RandomizedSearchCV.
    """
    if tune and X_train is not None and y_train is not None:
        print("    [Tuning] XGBoost Classifier via RandomizedSearchCV...")
        param_grid = {
            'n_estimators':     [300, 500, 700],
            'learning_rate':    [0.01, 0.03, 0.05, 0.1],
            'max_depth':        [3, 4, 5, 6],
            'subsample':        [0.6, 0.7, 0.8, 0.9],
            'colsample_bytree': [0.5, 0.6, 0.7, 0.8],
            'min_child_weight': [1, 3, 5],
            'gamma':            [0, 0.1, 0.2],
            'reg_alpha':        [0, 0.1, 0.5],
            'reg_lambda':       [0.5, 1.0, 1.5],
        }
        tscv = TimeSeriesSplit(n_splits=5)
        base = XGBClassifier(
            num_class=n_classes, objective='multi:softmax',
            random_state=42, n_jobs=-1, verbosity=0, tree_method='hist'
        )
        search = RandomizedSearchCV(
            base, param_grid, n_iter=40, cv=tscv,
            scoring='accuracy', random_state=42, n_jobs=-1, verbose=0
        )
        search.fit(X_train, y_train)
        print(f"    [Best XGB Params]   {search.best_params_}")
        print(f"    [Best XGB CV Acc]   {search.best_score_:.4f} ({search.best_score_*100:.2f}%)")
        return search.best_estimator_
    else:
        return XGBClassifier(
            n_estimators=500, learning_rate=0.05, max_depth=5,
            subsample=0.8, colsample_bytree=0.7,
            min_child_weight=3, gamma=0.1,
            reg_alpha=0.1, reg_lambda=1.0,
            num_class=n_classes, objective='multi:softmax',
            random_state=42, n_jobs=-1,
            verbosity=0, tree_method='hist'
        )


def train_all_classifiers(X_train, y_train, tune_hyperparams=True):
    """Training semua model KLASIFIKASI."""
    n_classes = len(np.unique(y_train))
    print(f"  Jumlah kelas: {n_classes} (nilai: {sorted(np.unique(y_train))})")

    print("\n  Membangun Logistic Regression Classifier...")
    lr = build_logistic_regression_clf()
    lr.fit(X_train, y_train)
    print("  ✅ Logistic Regression selesai")

    print("\n  Membangun Random Forest Classifier...")
    rf = build_random_forest_clf(tune=tune_hyperparams, X_train=X_train, y_train=y_train)
    if not tune_hyperparams:
        rf.fit(X_train, y_train)
    print("  ✅ Random Forest Classifier selesai")

    print("\n  Membangun XGBoost Classifier...")
    xgb = build_xgboost_clf(
        tune=tune_hyperparams, X_train=X_train, y_train=y_train, n_classes=n_classes
    )
    if not tune_hyperparams:
        xgb.fit(X_train, y_train)
    print("  ✅ XGBoost Classifier selesai")

    return {
        'Linear Regression': lr,   # Label tetap sama untuk konsistensi laporan
        'Random Forest':     rf,
        'XGBoost':           xgb,
    }


def get_feature_importance(model, feature_names: list, model_name: str):
    """Ambil feature importance untuk semua model."""
    if hasattr(model, 'feature_importances_'):
        importances = model.feature_importances_
    elif hasattr(model, 'coef_'):
        coef = model.coef_
        if coef.ndim > 1:
            importances = np.abs(coef).mean(axis=0)
        else:
            importances = np.abs(coef)
    else:
        importances = np.zeros(len(feature_names))

    total = importances.sum()
    if total > 0:
        importances = importances / total

    return dict(zip(feature_names, importances))
