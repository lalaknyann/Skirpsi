import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler

# Set theme
sns.set_theme(style="whitegrid")

# Custom colors matching the user's reference image
colors_before = ['#6ba4e8', '#e88ba5', '#ff6b8b'] # Light blue, light pink, rose red
colors_after = ['#3d4da8', '#9e3da8', '#c93446']  # Dark blue/navy, purple, crimson/dark red

def create_scaler_plot(data_path, output_image_name):
    # Load and parse data
    from ml_indibiz.preprocessing import load_and_parse, feature_engineering
    
    df_raw = load_and_parse(data_path)
    df = feature_engineering(df_raw)
    
    features = ['Facebook', 'Instagram', 'TikTok']
    
    # 1. Scale features
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(df[features])
    df_scaled = pd.DataFrame(scaled_features, columns=features)
    
    # Create 2x3 subplot grid
    fig, axes = plt.subplots(2, 3, figsize=(15, 8.5))
    
    # Main title
    fig.suptitle("Perbandingan Distribusi Fitur Sebelum vs Sesudah Standarisasi (StandardScaler)", 
                 fontsize=16, fontweight='bold', y=0.98)
    
    # Plot Before (Row 1)
    for idx, feature in enumerate(features):
        ax = axes[0, idx]
        sns.histplot(df[feature], kde=True, color=colors_before[idx], ax=ax, bins=25)
        ax.set_title(f"{feature} Views (Asli)", fontsize=12, fontweight='bold')
        ax.set_xlabel("Views", fontsize=10)
        ax.set_ylabel("Count", fontsize=10)
        
    # Plot After (Row 2)
    for idx, feature in enumerate(features):
        ax = axes[1, idx]
        sns.histplot(df_scaled[feature], kde=True, color=colors_after[idx], ax=ax, bins=25)
        ax.set_title(f"{feature} (Standarisasi Z-Score)", fontsize=12, fontweight='bold')
        ax.set_xlabel("Nilai Skala", fontsize=10)
        ax.set_ylabel("Count", fontsize=10)
        
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    
    # Save image
    artifact_dir = r"C:\Users\Administrator\.gemini\antigravity-ide\brain\3e51b5ac-1ede-43da-8c64-35e20520a4d8"
    if not os.path.exists(artifact_dir):
        os.makedirs(artifact_dir)
        
    save_path = os.path.join(artifact_dir, output_image_name)
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    # Print statistics for console/log
    print(f"\n================ STATISTICS FOR {data_path} ================")
    print("\n--- SEBELUM STANDARD SCALER ---")
    print(df[features].describe().loc[['mean', 'std', 'min', 'max']].to_string())
    print("\n--- SESUDAH STANDARD SCALER ---")
    print(df_scaled[features].describe().loc[['mean', 'std', 'min', 'max']].round(4).to_string())
    print(f"Saved plot to: {save_path}")

if __name__ == "__main__":
    if os.path.exists("Data Harian.csv"):
        create_scaler_plot("Data Harian.csv", "scaler_comparison_root.png")
    if os.path.exists("data/Data Harian.csv"):
        create_scaler_plot("data/Data Harian.csv", "scaler_comparison_data.png")
