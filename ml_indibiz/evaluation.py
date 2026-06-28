"""
evaluation.py
Evaluasi model: MAE, RMSE, R² (Regresi) + Accuracy, F1, Confusion Matrix (Klasifikasi)
Versi 3.0
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
from sklearn.metrics import (mean_absolute_error, mean_squared_error, r2_score,
                              accuracy_score, f1_score, classification_report,
                              confusion_matrix)
import os
import json

# Style konsisten
COLORS = {
    'Linear Regression': '#6C63FF',
    'Random Forest':     '#00D4A0',
    'XGBoost':          '#FF6B6B',
    'actual':           '#FFA500',
}
BG_COLOR   = '#0F0F1A'
CARD_COLOR = '#1A1A2E'
TEXT_COLOR = '#E0E0E0'
GRID_COLOR = '#2A2A4A'
ACCENT     = '#FFD700'


def set_dark_style():
    plt.rcParams.update({
        'figure.facecolor':  BG_COLOR,
        'axes.facecolor':    CARD_COLOR,
        'axes.edgecolor':    GRID_COLOR,
        'axes.labelcolor':   TEXT_COLOR,
        'xtick.color':       TEXT_COLOR,
        'ytick.color':       TEXT_COLOR,
        'text.color':        TEXT_COLOR,
        'grid.color':        GRID_COLOR,
        'grid.alpha':        0.4,
        'font.family':       'DejaVu Sans',
        'font.size':         11,
        'axes.titlesize':    13,
        'axes.titleweight':  'bold',
        'legend.facecolor':  CARD_COLOR,
        'legend.edgecolor':  GRID_COLOR,
        'legend.labelcolor': TEXT_COLOR,
    })


# ─────────────────────────────────────────────
#  EVALUASI REGRESI
# ─────────────────────────────────────────────

def compute_metrics(y_true, y_pred, model_name: str) -> dict:
    """Hitung MAE, RMSE, R² untuk satu model regresi."""
    mae  = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2   = r2_score(y_true, y_pred)

    return {
        'model':   model_name,
        'MAE':     round(mae, 4),
        'RMSE':    round(rmse, 4),
        'R2':      round(r2, 4),
        'R2_pct':  round(r2 * 100, 2),
    }


def evaluate_all_models(trained_models, X_test, y_test) -> dict:
    """Evaluasi semua model REGRESI."""
    results   = {}
    all_preds = {}

    for name, model in trained_models.items():
        y_pred = model.predict(X_test)
        metrics = compute_metrics(y_test, y_pred, name)
        results[name]   = metrics
        all_preds[name] = y_pred

        print(f"\n{'='*50}")
        print(f"  Model : {name}")
        print(f"  MAE   : {metrics['MAE']:.4f}")
        print(f"  RMSE  : {metrics['RMSE']:.4f}")
        print(f"  R²    : {metrics['R2']:.4f}  ({metrics['R2_pct']}%)")
        print(f"{'='*50}")

    return results, all_preds


# ─────────────────────────────────────────────
#  EVALUASI KLASIFIKASI
# ─────────────────────────────────────────────

def compute_classification_metrics(y_true, y_pred, model_name: str) -> dict:
    """Hitung Accuracy, F1, dll untuk satu model klasifikasi."""
    acc      = accuracy_score(y_true, y_pred)
    f1_macro = f1_score(y_true, y_pred, average='macro', zero_division=0)
    f1_w     = f1_score(y_true, y_pred, average='weighted', zero_division=0)

    return {
        'model':       model_name,
        'Accuracy':    round(acc, 4),
        'Accuracy_pct': round(acc * 100, 2),
        'F1_macro':    round(f1_macro, 4),
        'F1_weighted': round(f1_w, 4),
        # Untuk kompatibilitas tampilan dashboard (gunakan Accuracy sebagai R²_pct)
        'R2':          round(acc, 4),
        'R2_pct':      round(acc * 100, 2),
        'MAE':         round(mean_absolute_error(y_true, y_pred), 4),
        'RMSE':        round(np.sqrt(mean_squared_error(y_true, y_pred)), 4),
    }


def evaluate_all_classifiers(trained_models, X_test, y_test) -> dict:
    """Evaluasi semua model KLASIFIKASI."""
    results   = {}
    all_preds = {}

    for name, model in trained_models.items():
        y_pred = model.predict(X_test)
        metrics = compute_classification_metrics(y_test, y_pred, name)
        results[name]   = metrics
        all_preds[name] = y_pred

        print(f"\n{'='*55}")
        print(f"  Model    : {name}")
        print(f"  Akurasi  : {metrics['Accuracy_pct']:.2f}%")
        print(f"  F1 (macro)   : {metrics['F1_macro']:.4f}")
        print(f"  F1 (weighted): {metrics['F1_weighted']:.4f}")
        print(f"  MAE (mean error): {metrics['MAE']:.4f}")
        print(f"{'='*55}")

        # Detail per kelas
        print(f"\n  Classification Report — {name}:")
        print(classification_report(y_test, y_pred, zero_division=0))

    return results, all_preds


# ─────────────────────────────────────────────
#  PLOT: Confusion Matrix (BARU untuk Klasifikasi)
# ─────────────────────────────────────────────

def plot_confusion_matrices(y_test, all_preds, output_dir: str,
                             labels=None, title_prefix='Multi-Class'):
    set_dark_style()
    n_models = len(all_preds)
    fig, axes = plt.subplots(1, n_models, figsize=(6 * n_models, 5))
    if n_models == 1:
        axes = [axes]
    fig.patch.set_facecolor(BG_COLOR)
    fig.suptitle(f'Confusion Matrix — {title_prefix} Classification',
                 fontsize=16, fontweight='bold', color=TEXT_COLOR, y=1.02)

    palette = [COLORS['Linear Regression'], COLORS['Random Forest'], COLORS['XGBoost']]

    # Tentukan label nama sesuai binary vs multi-class
    is_binary = (labels is not None and len(labels) == 2)
    if is_binary:
        tick_labels = ['Rendah\n(0,1)', 'Tinggi\n(2,3)']
    else:
        tick_labels = [str(l) for l in labels] if labels is not None else None

    for i, (ax, (name, y_pred)) in enumerate(zip(axes, all_preds.items())):
        cm    = confusion_matrix(y_test, y_pred, labels=labels)
        acc   = accuracy_score(y_test, y_pred)
        color = palette[i % len(palette)]

        from matplotlib.colors import LinearSegmentedColormap
        cmap = LinearSegmentedColormap.from_list('model_cmap', [CARD_COLOR, color])

        sns.heatmap(cm, annot=True, fmt='d', cmap=cmap, ax=ax,
                    linewidths=0.5, linecolor=GRID_COLOR,
                    cbar_kws={'shrink': 0.8},
                    annot_kws={'size': 14, 'color': TEXT_COLOR})
        ax.set_title(f'{name}\nAkurasi: {acc*100:.2f}%', color=TEXT_COLOR, fontsize=12)
        ax.set_xlabel('Predicted', color=TEXT_COLOR)
        ax.set_ylabel('Actual',    color=TEXT_COLOR)
        if tick_labels is not None:
            ax.set_xticklabels(tick_labels, color=TEXT_COLOR)
            ax.set_yticklabels(tick_labels, color=TEXT_COLOR, rotation=0)
        ax.tick_params(colors=TEXT_COLOR)

    plt.tight_layout()
    path = os.path.join(output_dir, 'confusion_matrix.png')
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor=BG_COLOR)
    plt.close()
    print(f"  [Saved] {path}")
    return path



# ─────────────────────────────────────────────
#  PLOT: Accuracy Bar Chart (Klasifikasi)
# ─────────────────────────────────────────────

def plot_accuracy_comparison(results_clf: dict, output_dir: str):
    set_dark_style()
    model_names  = list(results_clf.keys())
    accuracies   = [results_clf[m]['Accuracy_pct'] for m in model_names]
    f1_macros    = [results_clf[m]['F1_macro'] * 100 for m in model_names]
    colors_list  = [COLORS[m] for m in model_names]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.patch.set_facecolor(BG_COLOR)
    fig.suptitle('Perbandingan Akurasi Klasifikasi — Linear Regression vs Random Forest vs XGBoost',
                 fontsize=14, fontweight='bold', color=TEXT_COLOR)

    # Accuracy
    bars = axes[0].bar(model_names, accuracies, color=colors_list, width=0.5,
                        edgecolor=GRID_COLOR, linewidth=0.8)
    # Target zone
    axes[0].axhspan(50, 70, alpha=0.15, color=ACCENT, label='Target 50-70%')
    axes[0].axhline(50, color=ACCENT, linewidth=1.5, linestyle='--', alpha=0.7)
    axes[0].axhline(70, color=ACCENT, linewidth=1.5, linestyle='--', alpha=0.7)

    best_idx = accuracies.index(max(accuracies))
    bars[best_idx].set_edgecolor(ACCENT)
    bars[best_idx].set_linewidth(3)

    for bar, val in zip(bars, accuracies):
        axes[0].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                     f'{val:.2f}%', ha='center', va='bottom',
                     fontsize=12, fontweight='bold', color=TEXT_COLOR)

    axes[0].set_title('Accuracy (%)', color=TEXT_COLOR)
    axes[0].set_ylabel('Akurasi (%)', color=TEXT_COLOR)
    axes[0].set_ylim(0, max(max(accuracies) * 1.3, 80))
    axes[0].tick_params(axis='x', rotation=15)
    axes[0].grid(axis='y', linestyle='--', alpha=0.3)
    axes[0].legend(fontsize=9)

    # F1 Macro
    bars2 = axes[1].bar(model_names, f1_macros, color=colors_list, width=0.5,
                         edgecolor=GRID_COLOR, linewidth=0.8)
    best_f1_idx = f1_macros.index(max(f1_macros))
    bars2[best_f1_idx].set_edgecolor(ACCENT)
    bars2[best_f1_idx].set_linewidth(3)

    for bar, val in zip(bars2, f1_macros):
        axes[1].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                     f'{val:.2f}%', ha='center', va='bottom',
                     fontsize=12, fontweight='bold', color=TEXT_COLOR)

    axes[1].set_title('F1-Score Macro (%)', color=TEXT_COLOR)
    axes[1].set_ylabel('F1-Score (%)', color=TEXT_COLOR)
    axes[1].set_ylim(0, max(max(f1_macros) * 1.3, 80))
    axes[1].tick_params(axis='x', rotation=15)
    axes[1].grid(axis='y', linestyle='--', alpha=0.3)

    plt.tight_layout()
    path = os.path.join(output_dir, 'accuracy_comparison.png')
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor=BG_COLOR)
    plt.close()
    print(f"  [Saved] {path}")
    return path


# ─────────────────────────────────────────────
#  PLOT: Actual vs Predicted (Regresi)
# ─────────────────────────────────────────────

def plot_actual_vs_predicted(y_test, all_preds, output_dir: str):
    set_dark_style()
    n_models = len(all_preds)
    fig, axes = plt.subplots(1, n_models, figsize=(6 * n_models, 5))
    if n_models == 1:
        axes = [axes]
    fig.patch.set_facecolor(BG_COLOR)
    fig.suptitle('Actual vs Predicted — Regresi', fontsize=16,
                 fontweight='bold', color=TEXT_COLOR, y=1.02)

    for ax, (name, y_pred) in zip(axes, all_preds.items()):
        ax.scatter(y_test, y_pred, alpha=0.6, s=25,
                   color=COLORS[name], edgecolors='none')
        lims = [min(y_test.min(), y_pred.min()) - 0.1,
                max(y_test.max(), y_pred.max()) + 0.1]
        ax.plot(lims, lims, '--', color=COLORS['actual'], linewidth=1.5, label='Perfect Fit')
        r2  = r2_score(y_test, y_pred)
        mae = mean_absolute_error(y_test, y_pred)
        ax.set_title(f'{name}\nR²={r2:.4f}  |  MAE={mae:.4f}', color=TEXT_COLOR)
        ax.set_xlabel('Actual', color=TEXT_COLOR)
        ax.set_ylabel('Predicted', color=TEXT_COLOR)
        ax.legend(fontsize=9)
        ax.grid(True, linestyle='--', alpha=0.3)

    plt.tight_layout()
    path = os.path.join(output_dir, 'actual_vs_predicted.png')
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor=BG_COLOR)
    plt.close()
    print(f"  [Saved] {path}")
    return path


# ─────────────────────────────────────────────
#  PLOT: Metrics Comparison (Regresi)
# ─────────────────────────────────────────────

def plot_metrics_comparison(results: dict, output_dir: str):
    set_dark_style()
    model_names  = list(results.keys())
    colors_list  = [COLORS[m] for m in model_names]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.patch.set_facecolor(BG_COLOR)
    fig.suptitle('Perbandingan Metrik Regresi', fontsize=14, fontweight='bold', color=TEXT_COLOR)

    for ax, (metric, label) in zip(axes, [
        ('MAE',  'MAE (↓ lebih baik)'),
        ('RMSE', 'RMSE (↓ lebih baik)'),
        ('R2',   'R² Score (↑ lebih baik)'),
    ]):
        vals = [results[m][metric] for m in model_names]
        bars = ax.bar(model_names, vals, color=colors_list, width=0.5,
                      edgecolor=GRID_COLOR, linewidth=0.8)
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + (max(vals) * 0.02 if max(vals) > 0 else 0.01),
                    f'{val:.4f}', ha='center', va='bottom',
                    fontsize=11, fontweight='bold', color=TEXT_COLOR)

        best_idx = vals.index(max(vals)) if metric == 'R2' else vals.index(min(vals))
        bars[best_idx].set_edgecolor(ACCENT)
        bars[best_idx].set_linewidth(2.5)

        ax.set_title(label, color=TEXT_COLOR)
        ax.set_ylabel(metric, color=TEXT_COLOR)
        ax.tick_params(axis='x', rotation=15)
        ax.grid(axis='y', linestyle='--', alpha=0.3)
        y_range = max(abs(v) for v in vals) * 1.4
        ax.set_ylim(min(min(vals) - y_range * 0.1, -0.05), y_range)

    plt.tight_layout()
    path = os.path.join(output_dir, 'metrics_comparison.png')
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor=BG_COLOR)
    plt.close()
    print(f"  [Saved] {path}")
    return path


# ─────────────────────────────────────────────
#  PLOT: Time Series
# ─────────────────────────────────────────────

def plot_time_series(y_test, all_preds, df_test_dates, output_dir: str):
    set_dark_style()
    fig, axes = plt.subplots(len(all_preds), 1, figsize=(14, 4 * len(all_preds)), sharex=True)
    if len(all_preds) == 1:
        axes = [axes]
    fig.patch.set_facecolor(BG_COLOR)
    fig.suptitle('Prediksi vs Aktual — Time Series (Test Set)',
                 fontsize=15, fontweight='bold', color=TEXT_COLOR)

    x = range(len(y_test))
    for ax, (name, y_pred) in zip(axes, all_preds.items()):
        ax.plot(x, y_test, color=COLORS['actual'], linewidth=1.5, alpha=0.9, label='Aktual', zorder=3)
        ax.plot(x, y_pred, color=COLORS[name], linewidth=1.5, alpha=0.8,
                linestyle='--', label=f'Prediksi ({name})', zorder=2)
        ax.fill_between(x, y_test, y_pred, alpha=0.12, color=COLORS[name])
        mae = mean_absolute_error(y_test, y_pred)
        ax.set_title(f'{name} — MAE: {mae:.4f}', color=TEXT_COLOR)
        ax.set_ylabel('Penjualan', color=TEXT_COLOR)
        ax.legend(loc='upper right', fontsize=9)
        ax.grid(True, linestyle='--', alpha=0.3)

    axes[-1].set_xlabel('Hari ke- (Test Set)', color=TEXT_COLOR)
    plt.tight_layout()
    path = os.path.join(output_dir, 'time_series_prediction.png')
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor=BG_COLOR)
    plt.close()
    print(f"  [Saved] {path}")
    return path


# ─────────────────────────────────────────────
#  PLOT: Feature Importance
# ─────────────────────────────────────────────

def plot_feature_importance(importance_dict: dict, output_dir: str, top_n: int = 15):
    set_dark_style()
    n_models = len(importance_dict)
    fig, axes = plt.subplots(1, n_models, figsize=(8 * n_models, 6))
    if n_models == 1:
        axes = [axes]
    fig.patch.set_facecolor(BG_COLOR)
    fig.suptitle('Feature Importance — Top Fitur Berpengaruh',
                 fontsize=15, fontweight='bold', color=TEXT_COLOR)

    for ax, (name, imp) in zip(axes, importance_dict.items()):
        sorted_imp = sorted(imp.items(), key=lambda x: x[1], reverse=True)[:top_n]
        features   = [x[0] for x in sorted_imp]
        values     = [x[1] for x in sorted_imp]

        bars = ax.barh(features[::-1], values[::-1], color=COLORS[name], alpha=0.85,
                       edgecolor=GRID_COLOR, linewidth=0.5)
        for bar, val in zip(bars, values[::-1]):
            ax.text(val + 0.001, bar.get_y() + bar.get_height() / 2,
                    f'{val:.3f}', va='center', fontsize=9, color=TEXT_COLOR)

        ax.set_title(f'{name}', color=TEXT_COLOR)
        ax.set_xlabel('Importance Score', color=TEXT_COLOR)
        ax.grid(axis='x', linestyle='--', alpha=0.3)

    plt.tight_layout()
    path = os.path.join(output_dir, 'feature_importance.png')
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor=BG_COLOR)
    plt.close()
    print(f"  [Saved] {path}")
    return path


# ─────────────────────────────────────────────
#  PLOT: Residuals
# ─────────────────────────────────────────────

def plot_residuals(y_test, all_preds, output_dir: str):
    set_dark_style()
    n_models = len(all_preds)
    fig, axes = plt.subplots(1, n_models, figsize=(6 * n_models, 5))
    if n_models == 1:
        axes = [axes]
    fig.patch.set_facecolor(BG_COLOR)
    fig.suptitle('Residual Plot', fontsize=15, fontweight='bold', color=TEXT_COLOR)

    for ax, (name, y_pred) in zip(axes, all_preds.items()):
        residuals = y_test - y_pred
        ax.scatter(y_pred, residuals, alpha=0.5, s=20, color=COLORS[name])
        ax.axhline(0, color=COLORS['actual'], linewidth=1.5, linestyle='--')
        ax.set_title(name, color=TEXT_COLOR)
        ax.set_xlabel('Predicted', color=TEXT_COLOR)
        ax.set_ylabel('Residual', color=TEXT_COLOR)
        ax.grid(True, linestyle='--', alpha=0.3)

    plt.tight_layout()
    path = os.path.join(output_dir, 'residuals.png')
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor=BG_COLOR)
    plt.close()
    print(f"  [Saved] {path}")
    return path


# ─────────────────────────────────────────────
#  Save Results JSON
# ─────────────────────────────────────────────

def _convert_keys(obj):
    if isinstance(obj, dict):
        return {str(k): _convert_keys(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_keys(v) for v in obj]
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    else:
        return obj


def save_results_json(results: dict, output_dir: str):
    path = os.path.join(output_dir, '..', 'results.json')
    path = os.path.normpath(path)
    results_clean = _convert_keys(results)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(results_clean, f, ensure_ascii=False, indent=2)
    print(f"  [Saved] {path}")
    return path
