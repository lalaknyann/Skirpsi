import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler

# Set aesthetic style
sns.set_theme(style="whitegrid")
plt.rcParams.update({
    'font.size': 10,
    'axes.labelsize': 12,
    'axes.titlesize': 14,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'figure.titlesize': 16
})

from ml_indibiz.preprocessing import load_and_parse, feature_engineering, get_full_feature_columns

def main():
    p1 = "Data Harian.csv"
    p2 = "data/Data Harian.csv"
    
    print("--- 1. MEMBANDINGKAN DATASET ---")
    df1 = None
    df2 = None
    
    if os.path.exists(p1):
        df1 = load_and_parse(p1)
        print(f"Dataset di Root (p1): {p1}")
        print(f"  Jumlah baris: {len(df1)}")
        print(f"  Rentang Tanggal: {df1['tanggal'].min().date()} s/d {df1['tanggal'].max().date()}")
        
    if os.path.exists(p2):
        df2 = load_and_parse(p2)
        print(f"Dataset di folder data/ (p2): {p2}")
        print(f"  Jumlah baris: {len(df2)}")
        print(f"  Rentang Tanggal: {df2['tanggal'].min().date()} s/d {df2['tanggal'].max().date()}")
        
    # Tentukan dataset baru (yang memiliki baris terbanyak atau tanggal terbaru)
    # Jika keduanya ada, kita bandingkan jumlah barisnya
    new_data_path = p2
    df_new = df2
    if df1 is not None and df2 is not None:
        if len(df1) > len(df2):
            new_data_path = p1
            df_new = df1
        elif df1['tanggal'].max() > df2['tanggal'].max():
            new_data_path = p1
            df_new = df1
            
    print(f"\n=> Menggunakan Dataset Baru: {new_data_path}")
    
    # 2. Feature Engineering
    df_fe = feature_engineering(df_new)
    
    # Ambil beberapa fitur penting untuk dianalisis
    features_to_plot = ['Facebook', 'Instagram', 'TikTok', 'total_views']
    
    # Tampilkan info sebelum StandardScaler
    print("\n--- 2. STATISTIK SEBELUM STANDARD SCALER ---")
    before_stats = df_fe[features_to_plot].describe().loc[['mean', 'std', 'min', 'max']]
    print(before_stats.to_string())
    
    # 3. Scaling menggunakan StandardScaler
    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(df_fe[features_to_plot])
    df_scaled = pd.DataFrame(scaled_data, columns=features_to_plot)
    
    # Tampilkan info setelah StandardScaler
    print("\n--- 3. STATISTIK SESUDAH STANDARD SCALER ---")
    after_stats = df_scaled[features_to_plot].describe().loc[['mean', 'std', 'min', 'max']]
    print(after_stats.round(4).to_string())
    
    # 4. Membuat Visualisasi
    fig, axes = plt.subplots(4, 2, figsize=(15, 18))
    fig.suptitle("Perbandingan Distribusi Fitur Sebelum & Sesudah StandardScaler\n(Dataset: {})".format(new_data_path), y=0.98, fontweight='bold')
    
    colors = ['#1877F2', '#E1306C', '#000000', '#4A90E2'] # FB, IG, TikTok, Total
    
    for i, col in enumerate(features_to_plot):
        # Sebelum Scaling (Kiri)
        sns.histplot(df_fe[col], kde=True, ax=axes[i, 0], color=colors[i], bins=20)
        axes[i, 0].set_title(f"Sebelum Scaling: {col}")
        axes[i, 0].set_xlabel("Nilai Asli")
        axes[i, 0].set_ylabel("Frekuensi")
        
        # Info text box untuk statistik sebelum scaling
        mean_val = df_fe[col].mean()
        std_val = df_fe[col].std()
        axes[i, 0].text(0.95, 0.95, f"Mean: {mean_val:.2f}\nStd: {std_val:.2f}", 
                        transform=axes[i, 0].transAxes, verticalalignment='top', horizontalalignment='right',
                        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        # Sesudah Scaling (Kanan)
        sns.histplot(df_scaled[col], kde=True, ax=axes[i, 1], color=colors[i], bins=20)
        axes[i, 1].set_title(f"Sesudah Scaling (StandardScaler): {col}")
        axes[i, 1].set_xlabel("Nilai Standardisasi (Z-Score)")
        axes[i, 1].set_ylabel("Frekuensi")
        
        # Info text box untuk statistik sesudah scaling
        mean_s = df_scaled[col].mean()
        std_s = df_scaled[col].std()
        axes[i, 1].text(0.95, 0.95, f"Mean: {mean_s:.2f}\nStd: {std_s:.2f}", 
                        transform=axes[i, 1].transAxes, verticalalignment='top', horizontalalignment='right',
                        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    # Save path ke folder artifact
    artifact_dir = r"C:\Users\Administrator\.gemini\antigravity-ide\brain\3e51b5ac-1ede-43da-8c64-35e20520a4d8"
    if not os.path.exists(artifact_dir):
        os.makedirs(artifact_dir)
        
    save_path = os.path.join(artifact_dir, "scaler_comparison.png")
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"\n✅ Plot visualisasi berhasil disimpan di: {save_path}")

if __name__ == "__main__":
    main()
