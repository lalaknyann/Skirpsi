"""
research_questions.py
Analisis visual untuk menjawab 4 pertanyaan penelitian skripsi
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
from sklearn.metrics import r2_score, mean_absolute_error
import os

BG_COLOR   = '#0F0F1A'
CARD_COLOR = '#1A1A2E'
TEXT_COLOR = '#E0E0E0'
GRID_COLOR = '#2A2A4A'
ACCENT1    = '#6C63FF'
ACCENT2    = '#00D4A0'
ACCENT3    = '#FF6B6B'
ACCENT4    = '#FFA500'


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
        'font.size':         10,
        'axes.titlesize':    12,
        'axes.titleweight':  'bold',
        'legend.facecolor':  CARD_COLOR,
        'legend.edgecolor':  GRID_COLOR,
        'legend.labelcolor': TEXT_COLOR,
    })


# ─────────────────────────────────────────────────────────
#  Q1: Sejauh mana pengaruh views terhadap penjualan?
#  → Heatmap korelasi + scatter views vs penjualan
# ─────────────────────────────────────────────────────────
def plot_q1_views_correlation(df, output_dir: str):
    set_dark_style()
    fig = plt.figure(figsize=(16, 6), facecolor=BG_COLOR)
    fig.suptitle(
        'Q1: Pengaruh Views Media Sosial terhadap Penjualan Indibiz',
        fontsize=14, fontweight='bold', color=TEXT_COLOR, y=1.01
    )

    gs = gridspec.GridSpec(1, 2, figure=fig, wspace=0.4)

    # --- Subplot 1: Heatmap Korelasi ---
    ax1 = fig.add_subplot(gs[0])
    cols = ['Facebook', 'Instagram', 'TikTok', 'total_views',
            'total_engagement', 'sentiment_score', 'Penjualan']
    corr_matrix = df[cols].corr()
    mask = np.zeros_like(corr_matrix, dtype=bool)
    mask[np.triu_indices_from(mask, k=1)] = True

    cmap = sns.diverging_palette(240, 10, as_cmap=True)
    sns.heatmap(
        corr_matrix, ax=ax1, annot=True, fmt='.2f', cmap=cmap,
        center=0, vmin=-1, vmax=1, square=True,
        linewidths=0.5, linecolor=GRID_COLOR,
        annot_kws={'size': 9, 'color': 'white'},
        cbar_kws={'shrink': 0.8}
    )
    ax1.set_title('Matriks Korelasi — Views vs Penjualan', color=TEXT_COLOR)
    ax1.tick_params(colors=TEXT_COLOR, rotation=45)

    # --- Subplot 2: Scatter Views vs Penjualan ---
    ax2 = fig.add_subplot(gs[1])
    colors_scatter = {
        'Facebook': ACCENT1, 'Instagram': ACCENT2, 'TikTok': ACCENT3
    }
    for platform, color in colors_scatter.items():
        ax2.scatter(df[platform] / 1000, df['Penjualan'],
                    alpha=0.35, s=15, color=color, label=platform)

    ax2.set_xlabel('Views (ribuan)', color=TEXT_COLOR)
    ax2.set_ylabel('Penjualan (unit)', color=TEXT_COLOR)
    ax2.set_title('Scatter: Views per Platform vs Penjualan', color=TEXT_COLOR)
    ax2.legend(fontsize=9, markerscale=2)
    ax2.grid(True, linestyle='--', alpha=0.3)

    plt.tight_layout()
    path = os.path.join(output_dir, 'q1_views_correlation.png')
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor=BG_COLOR)
    plt.close()
    print(f"  [Saved] {path}")
    return path


# ─────────────────────────────────────────────────────────
#  Q2: Pengaruh Engagement terhadap Penjualan
#  → Bar chart korelasi engagement vs penjualan + scatter
# ─────────────────────────────────────────────────────────
def plot_q2_engagement_effect(df, output_dir: str):
    set_dark_style()
    fig, axes = plt.subplots(1, 2, figsize=(15, 6), facecolor=BG_COLOR)
    fig.suptitle(
        'Q2: Pengaruh Engagement Media Sosial terhadap Penjualan Indibiz',
        fontsize=14, fontweight='bold', color=TEXT_COLOR
    )

    # --- Subplot 1: Bar Korelasi ---
    ax1 = axes[0]
    # Gunakan hanya kolom yang tersedia di dataframe
    all_engagement_cols = ['likes_ig', 'likes_fb', 'likes_tt', 'comments_ig', 'comments_fb',
                           'total_engagement', 'log_engagement', 'sentiment_score']
    engagement_cols = [c for c in all_engagement_cols if c in df.columns]
    corr_vals = [df[col].corr(df['Penjualan']) for col in engagement_cols]
    labels_map = {
        'likes_ig': 'Likes IG', 'likes_fb': 'Likes FB', 'likes_tt': 'Likes TikTok',
        'comments_ig': 'Comments IG', 'comments_fb': 'Comments FB',
        'total_engagement': 'Total Engagement', 'log_engagement': 'Log Engagement',
        'sentiment_score': 'Sentiment Score'
    }
    labels = [labels_map.get(c, c) for c in engagement_cols]
    colors_bar = [ACCENT1 if v >= 0 else ACCENT3 for v in corr_vals]

    bars = ax1.barh(labels, corr_vals, color=colors_bar, edgecolor=GRID_COLOR, height=0.6)
    ax1.axvline(0, color=TEXT_COLOR, linewidth=0.8, linestyle='--')
    for bar, val in zip(bars, corr_vals):
        ax1.text(val + (0.005 if val >= 0 else -0.005),
                 bar.get_y() + bar.get_height() / 2,
                 f'{val:.3f}', va='center', fontsize=9,
                 ha='left' if val >= 0 else 'right', color=TEXT_COLOR)
    ax1.set_xlabel('Korelasi Pearson dengan Penjualan', color=TEXT_COLOR)
    ax1.set_title('Korelasi Engagement vs Penjualan', color=TEXT_COLOR)
    ax1.grid(axis='x', linestyle='--', alpha=0.3)

    # --- Subplot 2: Total Engagement vs Penjualan Scatter ---
    ax2 = axes[1]
    sc = ax2.scatter(df['total_engagement'] / 1000, df['Penjualan'],
                     c=df['sentiment_score'], cmap='plasma',
                     alpha=0.5, s=20, edgecolors='none')
    cbar = plt.colorbar(sc, ax=ax2)
    cbar.set_label('Sentiment Score', color=TEXT_COLOR)
    cbar.ax.yaxis.set_tick_params(color=TEXT_COLOR)
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color=TEXT_COLOR)

    ax2.set_xlabel('Total Engagement (ribuan)', color=TEXT_COLOR)
    ax2.set_ylabel('Penjualan (unit)', color=TEXT_COLOR)
    ax2.set_title('Total Engagement + Sentimen vs Penjualan', color=TEXT_COLOR)
    ax2.grid(True, linestyle='--', alpha=0.3)

    plt.tight_layout()
    path = os.path.join(output_dir, 'q2_engagement_effect.png')
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor=BG_COLOR)
    plt.close()
    print(f"  [Saved] {path}")
    return path


# ─────────────────────────────────────────────────────────
#  Q3: Perbandingan akurasi 3 model ML
#  → Radar chart + tabel metrik
# ─────────────────────────────────────────────────────────
def plot_q3_model_comparison(results: dict, output_dir: str):
    set_dark_style()
    fig, axes = plt.subplots(1, 2, figsize=(15, 6), facecolor=BG_COLOR)

    # Deteksi apakah ini hasil klasifikasi atau regresi
    sample = list(results.values())[0]
    is_clf = 'Accuracy_pct' in sample
    metric_key  = 'Accuracy_pct' if is_clf else 'R2_pct'
    metric_label = 'Akurasi (%)' if is_clf else 'R² Score (%%)'
    chart_title = ('Q3: Perbandingan Akurasi Klasifikasi — '
                   'Linear Regression vs Random Forest vs XGBoost')

    fig.suptitle(chart_title, fontsize=14, fontweight='bold', color=TEXT_COLOR)

    model_names  = list(results.keys())
    model_colors = [ACCENT1, ACCENT2, ACCENT3]

    # --- Subplot 1: Accuracy / R² ---
    ax1 = axes[0]
    acc_vals = [results[m][metric_key] for m in model_names]
    mae_vals = [results[m]['MAE']       for m in model_names]

    bars1 = ax1.bar(model_names, acc_vals, color=model_colors, alpha=0.85,
                    edgecolor=GRID_COLOR, width=0.5)

    if is_clf:
        # Gambar zona target 50-70%
        ax1.axhspan(50, 70, alpha=0.12, color='#FFD700', label='Target 50-70%')
        ax1.axhline(50, color='#FFD700', linewidth=1.5, linestyle='--', alpha=0.7)
        ax1.axhline(70, color='#FFD700', linewidth=1.5, linestyle='--', alpha=0.7)
        ax1.legend(fontsize=9)

    y_max = max(max(acc_vals) * 1.3, 80) if is_clf else max(acc_vals) * 1.4
    ax1.set_ylim(0, y_max)
    ax1.set_ylabel(metric_label, color=TEXT_COLOR)
    ax1.set_title(f'{"Akurasi" if is_clf else "R² Score"} per Model', color=TEXT_COLOR)
    ax1.tick_params(axis='x', rotation=10)
    ax1.grid(axis='y', linestyle='--', alpha=0.3)

    for bar, val in zip(bars1, acc_vals):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + (y_max * 0.02),
                 f'{val:.2f}%', ha='center', va='bottom',
                 fontsize=11, fontweight='bold', color=TEXT_COLOR)

    best_idx = acc_vals.index(max(acc_vals))
    bars1[best_idx].set_edgecolor('#FFD700')
    bars1[best_idx].set_linewidth(3)

    # --- Subplot 2: MAE ---
    ax2 = axes[1]
    bars2 = ax2.bar(model_names, mae_vals, color=model_colors, alpha=0.8,
                    edgecolor=GRID_COLOR, width=0.5)
    ax2.set_ylabel('MAE (Mean Absolute Error)', color=TEXT_COLOR)
    ax2.set_title('MAE per Model — ↓ Lebih Baik', color=TEXT_COLOR)
    ax2.tick_params(axis='x', rotation=10)
    ax2.grid(axis='y', linestyle='--', alpha=0.3)
    ax2.set_ylim(0, max(mae_vals) * 1.3)

    for bar, val in zip(bars2, mae_vals):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + (max(mae_vals) * 0.02),
                 f'{val:.4f}', ha='center', va='bottom',
                 fontsize=10, fontweight='bold', color=TEXT_COLOR)

    best_mae_idx = mae_vals.index(min(mae_vals))
    bars2[best_mae_idx].set_edgecolor('#FFD700')
    bars2[best_mae_idx].set_linewidth(2.5)

    plt.tight_layout()
    path = os.path.join(output_dir, 'q3_model_comparison.png')
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor=BG_COLOR)
    plt.close()
    print(f"  [Saved] {path}")
    return path


# ─────────────────────────────────────────────────────────
#  Q4: Pengaruh Sentimen terhadap Model Prediksi
#  → Bandingkan R² & MAE model dengan/tanpa fitur sentimen
# ─────────────────────────────────────────────────────────
def plot_q4_sentiment_impact(results_with: dict, results_without: dict, output_dir: str):
    set_dark_style()
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), facecolor=BG_COLOR)
    fig.suptitle(
        'Q4: Dampak Sentimen Pelanggan terhadap Akurasi Model Prediksi',
        fontsize=14, fontweight='bold', color=TEXT_COLOR
    )

    model_names = list(results_with.keys())
    x = np.arange(len(model_names))
    width = 0.35

    # Deteksi klasifikasi vs regresi
    sample_w = list(results_with.values())[0]
    is_clf   = 'Accuracy_pct' in sample_w
    r2_label = 'Akurasi (%)' if is_clf else 'R² Score'
    r2_key   = 'Accuracy_pct' if is_clf else 'R2_pct'

    # --- Accuracy / R² comparison ---
    ax1 = axes[0]
    r2_with    = [results_with[m][r2_key]    for m in model_names]
    r2_without = [results_without[m][r2_key] for m in model_names]

    b1 = ax1.bar(x - width / 2, r2_with,    width, label='Dengan Sentimen',  color=ACCENT2, alpha=0.85)
    b2 = ax1.bar(x + width / 2, r2_without, width, label='Tanpa Sentimen',   color=ACCENT3, alpha=0.85)
    ax1.set_xticks(x)
    ax1.set_xticklabels(model_names, rotation=10, fontsize=9)
    ax1.set_ylabel(r2_label, color=TEXT_COLOR)
    ax1.set_title(f'{r2_label}: Dengan vs Tanpa Fitur Sentimen', color=TEXT_COLOR)
    ax1.legend()
    ax1.grid(axis='y', linestyle='--', alpha=0.3)
    all_r2 = r2_with + r2_without
    ax1.set_ylim(0, max(max(all_r2) * 1.3, 1.0))

    for bar, val in zip(b1, r2_with):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 f'{val:.2f}%' if is_clf else f'{val:.3f}',
                 ha='center', va='bottom', fontsize=8, color=TEXT_COLOR)
    for bar, val in zip(b2, r2_without):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 f'{val:.2f}%' if is_clf else f'{val:.3f}',
                 ha='center', va='bottom', fontsize=8, color=TEXT_COLOR)

    # --- MAE comparison ---
    ax2 = axes[1]
    mae_with    = [results_with[m]['MAE']    for m in model_names]
    mae_without = [results_without[m]['MAE'] for m in model_names]

    b3 = ax2.bar(x - width / 2, mae_with,    width, label='Dengan Sentimen',  color=ACCENT2, alpha=0.85)
    b4 = ax2.bar(x + width / 2, mae_without, width, label='Tanpa Sentimen',   color=ACCENT3, alpha=0.85)
    ax2.set_xticks(x)
    ax2.set_xticklabels(model_names, rotation=10, fontsize=9)
    ax2.set_ylabel('MAE', color=TEXT_COLOR)
    ax2.set_title('MAE: Dengan vs Tanpa Fitur Sentimen (↓ Lebih Baik)', color=TEXT_COLOR)
    ax2.legend()
    ax2.grid(axis='y', linestyle='--', alpha=0.3)
    all_mae = mae_with + mae_without
    ax2.set_ylim(0, max(all_mae) * 1.3)

    for bar, val in zip(b3, mae_with):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + (max(all_mae) * 0.02),
                 f'{val:.3f}', ha='center', va='bottom', fontsize=8, color=TEXT_COLOR)
    for bar, val in zip(b4, mae_without):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + (max(all_mae) * 0.02),
                 f'{val:.3f}', ha='center', va='bottom', fontsize=8, color=TEXT_COLOR)

    plt.tight_layout()
    path = os.path.join(output_dir, 'q4_sentiment_impact.png')
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor=BG_COLOR)
    plt.close()
    print(f"  [Saved] {path}")
    return path


# ─────────────────────────────────────────────────────────
#  Bonus: Monthly Trend Views vs Penjualan
# ─────────────────────────────────────────────────────────
def plot_monthly_trend(df, output_dir: str):
    set_dark_style()
    df_monthly = df.groupby(['tahun', 'bulan']).agg({
        'Facebook': 'mean', 'Instagram': 'mean', 'TikTok': 'mean',
        'Penjualan': 'sum', 'total_views': 'mean'
    }).reset_index()
    df_monthly['period'] = df_monthly.apply(
        lambda r: f"{int(r['bulan']):02d}/{int(r['tahun'])}", axis=1
    )

    fig, ax1 = plt.subplots(figsize=(16, 6), facecolor=BG_COLOR)
    fig.suptitle('Tren Bulanan Views Media Sosial vs Total Penjualan Indibiz',
                 fontsize=14, fontweight='bold', color=TEXT_COLOR)

    ax1.set_facecolor(CARD_COLOR)
    x = range(len(df_monthly))
    ax1.plot(x, df_monthly['Facebook'],  color=ACCENT1, linewidth=2, label='Facebook Views', marker='o', markersize=3)
    ax1.plot(x, df_monthly['Instagram'], color=ACCENT2, linewidth=2, label='Instagram Views', marker='s', markersize=3)
    ax1.plot(x, df_monthly['TikTok'],    color=ACCENT3, linewidth=2, label='TikTok Views',    marker='^', markersize=3)
    ax1.set_ylabel('Rata-rata Views', color=TEXT_COLOR)
    ax1.set_xticks(x)
    ax1.set_xticklabels(df_monthly['period'], rotation=45, fontsize=7)
    ax1.grid(True, linestyle='--', alpha=0.3)
    ax1.legend(loc='upper left', fontsize=9)

    ax2 = ax1.twinx()
    ax2.set_facecolor(CARD_COLOR)
    ax2.bar(x, df_monthly['Penjualan'], alpha=0.3, color=ACCENT4, label='Total Penjualan')
    ax2.set_ylabel('Total Penjualan (unit)', color=ACCENT4)
    ax2.spines['right'].set_color(ACCENT4)
    ax2.yaxis.label.set_color(ACCENT4)
    ax2.tick_params(axis='y', colors=ACCENT4)
    ax2.legend(loc='upper right', fontsize=9)

    plt.tight_layout()
    path = os.path.join(output_dir, 'monthly_trend.png')
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor=BG_COLOR)
    plt.close()
    print(f"  [Saved] {path}")
    return path
