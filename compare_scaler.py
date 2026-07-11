import os
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler

# Let's load preprocessing modules
from ml_indibiz.preprocessing import load_and_parse, feature_engineering, get_views_only_feature_columns, get_full_feature_columns

def analyze_dataset(path):
    print(f"\n==================================================")
    print(f"ANALYZING DATASET: {path}")
    print(f"==================================================")
    
    if not os.path.exists(path):
        print("File does not exist.")
        return
        
    df_raw = load_and_parse(path)
    print(f"Raw rows: {len(df_raw)}")
    print(f"Date range: {df_raw['tanggal'].min().date()} to {df_raw['tanggal'].max().date()}")
    
    # Feature engineering
    df = feature_engineering(df_raw)
    print(f"Rows after feature engineering: {len(df)}")
    
    # Let's choose some key features to show:
    # 1. Raw views: Facebook, Instagram, TikTok
    # 2. Total views: total_views
    # 3. Log views: log_total_views
    # 4. A temporal feature: hari
    # 5. Lag/rolling feature (if present in full features): penjualan_lag1, sales_roll3_mean
    
    key_features = ['Facebook', 'Instagram', 'TikTok', 'total_views', 'log_total_views', 'hari']
    available_features = [f for f in key_features if f in df.columns]
    
    # For full features
    full_cols = get_full_feature_columns()
    full_cols = [c for c in full_cols if c in df.columns]
    
    # Values BEFORE scaler
    print("\n--- STATISTIK SEBELUM STANDARD SCALER ---")
    before_stats = df[available_features].describe().loc[['mean', 'std', 'min', 'max']]
    print(before_stats)
    
    # Scale data
    X = df[full_cols].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Map back scaled columns
    df_scaled = pd.DataFrame(X_scaled, columns=full_cols)
    
    # Values AFTER scaler
    print("\n--- STATISTIK SESUDAH STANDARD SCALER ---")
    after_stats = df_scaled[available_features].describe().loc[['mean', 'std', 'min', 'max']]
    print(after_stats.round(4))
    
    # Detailed sample comparisons (first 5 rows)
    print("\n--- PERBANDINGAN NILAI BARIS (5 BARIS PERTAMA) ---")
    for col in available_features:
        print(f"\nFitur: {col}")
        comp_df = pd.DataFrame({
            'Sebelum Scaling': df[col].head(5),
            'Sesudah Scaling': df_scaled[col].head(5)
        })
        print(comp_df)

if __name__ == "__main__":
    analyze_dataset("Data Harian.csv")
    analyze_dataset("data/Data Harian.csv")
