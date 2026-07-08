"""
preprocessing.py
Modul preprocessing data untuk prediksi penjualan Indibiz
Versi 3.0 — Dual approach: Regression + Classification
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
import warnings
warnings.filterwarnings('ignore')


def load_and_parse(csv_url: str) -> pd.DataFrame:
    """
    Load dataset dari URL Google Sheets CSV atau file lokal.
    Kolom: id, tanggal, Facebook, Instagram, TikTok, Penjualan
    """
    df = pd.read_csv(csv_url, usecols=range(6))
    df.columns = ['id', 'tanggal', 'Facebook', 'Instagram', 'TikTok', 'Penjualan']

    # ==== Parsing Tanggal ====
    bulan_id = {
        'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
        'Mei': '05', 'Jun': '06', 'Jul': '07', 'Agu': '08',
        'Sep': '09', 'Okt': '10', 'Nov': '11', 'Des': '12'
    }

    def parse_tanggal(tgl_str):
        tgl_str = str(tgl_str).strip()
        for id_name, num in bulan_id.items():
            tgl_str = tgl_str.replace(id_name, num)
        try:
            return pd.to_datetime(tgl_str, format='%d %m %Y')
        except Exception:
            try:
                return pd.to_datetime(tgl_str, infer_datetime_format=True)
            except Exception:
                return pd.NaT

    df['tanggal'] = df['tanggal'].apply(parse_tanggal)
    df = df.dropna(subset=['tanggal'])
    df = df.sort_values('tanggal').reset_index(drop=True)

    for col in ['Facebook', 'Instagram', 'TikTok', 'Penjualan']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df = df.dropna().reset_index(drop=True)
    return df


def feature_engineering(df: pd.DataFrame) -> pd.DataFrame:
    """
    Feature Engineering Versi 3.0
    Fokus pada fitur temporal & views yang relevan untuk prediksi 0/1/2/3.
    """
    df = df.copy()

    # ==== 1. Fitur Temporal ====
    df['hari']        = df['tanggal'].dt.day
    df['bulan']       = df['tanggal'].dt.month
    df['tahun']       = df['tanggal'].dt.year
    df['hari_pekan']  = df['tanggal'].dt.dayofweek   # 0=Senin, 6=Minggu
    df['is_weekend']  = (df['hari_pekan'] >= 5).astype(int)
    df['quarter']     = df['tanggal'].dt.quarter
    df['day_of_year'] = df['tanggal'].dt.dayofyear
    df['week_of_year']= df['tanggal'].dt.isocalendar().week.astype(int)

    # Cyclical encoding
    df['bulan_sin']   = np.sin(2 * np.pi * df['bulan'] / 12)
    df['bulan_cos']   = np.cos(2 * np.pi * df['bulan'] / 12)
    df['dow_sin']     = np.sin(2 * np.pi * df['hari_pekan'] / 7)
    df['dow_cos']     = np.cos(2 * np.pi * df['hari_pekan'] / 7)

    # Bulan penting
    df['is_peak_month'] = df['bulan'].isin([3, 4, 12]).astype(int)
    df['is_mid_year']   = df['bulan'].isin([6, 7]).astype(int)
    df['is_q4']         = (df['quarter'] == 4).astype(int)

    # ==== 2. Log-transform Views ====
    for col in ['Facebook', 'Instagram', 'TikTok']:
        df[f'log_{col.lower()}'] = np.log1p(df[col])

    df['total_views']     = df['Facebook'] + df['Instagram'] + df['TikTok']
    df['log_total_views'] = np.log1p(df['total_views'])

    # Rasio
    df['ratio_fb_total'] = df['Facebook']  / (df['total_views'] + 1)
    df['ratio_ig_total'] = df['Instagram'] / (df['total_views'] + 1)
    df['ratio_tt_total'] = df['TikTok']    / (df['total_views'] + 1)

    # ==== 3. Growth Rate Views ====
    for col in ['Facebook', 'Instagram', 'TikTok', 'total_views']:
        prev = df[col].shift(1).replace(0, np.nan)
        df[f'{col.lower()}_growth'] = ((df[col] - df[col].shift(1)) / prev).fillna(0).clip(-2, 2)

    # ==== 4. Lag Penjualan ====
    for lag in [1, 2, 3, 7, 14]:
        df[f'penjualan_lag{lag}'] = df['Penjualan'].shift(lag)

    # ==== 5. Lag Views ====
    for lag in [1, 3, 7]:
        df[f'fb_lag{lag}']  = df['Facebook'].shift(lag)
        df[f'ig_lag{lag}']  = df['Instagram'].shift(lag)
        df[f'tt_lag{lag}']  = df['TikTok'].shift(lag)

    # ==== 6. Rolling Statistics Penjualan ====
    df['sales_roll3_mean']  = df['Penjualan'].shift(1).rolling(window=3,  min_periods=1).mean()
    df['sales_roll7_mean']  = df['Penjualan'].shift(1).rolling(window=7,  min_periods=1).mean()
    df['sales_roll14_mean'] = df['Penjualan'].shift(1).rolling(window=14, min_periods=1).mean()
    df['sales_roll7_std']   = df['Penjualan'].shift(1).rolling(window=7,  min_periods=1).std().fillna(0)
    df['sales_roll7_max']   = df['Penjualan'].shift(1).rolling(window=7,  min_periods=1).max()

    # ==== 7. Rolling Statistics Views ====
    df['views_roll7_mean']  = df['total_views'].shift(1).rolling(window=7,  min_periods=1).mean()
    df['views_roll14_mean'] = df['total_views'].shift(1).rolling(window=14, min_periods=1).mean()
    df['views_roll7_std']   = df['total_views'].shift(1).rolling(window=7,  min_periods=1).std().fillna(0)

    # ==== 8. Trend ====
    df['sales_trend']  = df['sales_roll7_mean']  - df['sales_roll14_mean']
    df['views_trend']  = df['views_roll7_mean']  - df['views_roll14_mean']

    # ==== 9. Views × Waktu Interaction ====
    df['log_views_x_weekend']   = df['log_total_views'] * df['is_weekend']
    df['log_views_x_peakmon']   = df['log_total_views'] * df['is_peak_month']
    df['log_views_x_q4']        = df['log_total_views'] * df['is_q4']

    # ==== 10. Target Klasifikasi: Binary (tinggi vs rendah) ====
    # 0-1 = rendah (0), 2-3 = tinggi (1)
    df['penjualan_binary'] = (df['Penjualan'] >= 2).astype(int)

    # Drop baris NaN dari lag/rolling
    df = df.dropna().reset_index(drop=True)

    return df


def get_views_only_feature_columns():
    """Daftar fitur views + temporal (TANPA lag/rolling penjualan)."""
    return [
        # Raw views
        'Facebook', 'Instagram', 'TikTok',
        'log_facebook', 'log_instagram', 'log_tiktok',
        'total_views', 'log_total_views',
        # Rasio
        'ratio_fb_total', 'ratio_ig_total', 'ratio_tt_total',
        # Growth
        'facebook_growth', 'instagram_growth', 'tiktok_growth', 'total_views_growth',
        # Temporal
        'hari', 'bulan', 'tahun', 'hari_pekan', 'is_weekend',
        'quarter', 'day_of_year', 'week_of_year',
        'bulan_sin', 'bulan_cos', 'dow_sin', 'dow_cos',
        'is_peak_month', 'is_mid_year', 'is_q4',
        # Lag views
        'fb_lag1', 'fb_lag3', 'fb_lag7',
        'ig_lag1', 'ig_lag3', 'ig_lag7',
        'tt_lag1', 'tt_lag3', 'tt_lag7',
        # Rolling views
        'views_roll7_mean', 'views_roll14_mean', 'views_roll7_std',
        # Trend views
        'views_trend',
        # Interaction
        'log_views_x_weekend', 'log_views_x_peakmon', 'log_views_x_q4',
    ]


def get_full_feature_columns():
    """Daftar fitur lengkap (views + temporal + lag/rolling penjualan)."""
    return get_views_only_feature_columns() + [
        # Lag penjualan
        'penjualan_lag1', 'penjualan_lag2', 'penjualan_lag3',
        'penjualan_lag7', 'penjualan_lag14',
        # Rolling penjualan
        'sales_roll3_mean', 'sales_roll7_mean', 'sales_roll14_mean',
        'sales_roll7_std', 'sales_roll7_max',
        # Trend penjualan
        'sales_trend',
    ]


def get_feature_columns():
    """Daftar kolom fitur default (full features)."""
    return get_full_feature_columns()


def get_feature_columns_no_sentiment():
    """Fitur tanpa sentimen (karena sudah dihapus, return get_full_feature_columns)."""
    return get_full_feature_columns()



def prepare_data(df: pd.DataFrame, feature_cols: list = None, test_size: float = 0.2, scale: bool = True):
    """
    Split data time-based untuk REGRESI.
    Returns: X_train, X_test, y_train, y_test, scaler, feature_cols
    """
    if feature_cols is None:
        feature_cols = get_feature_columns()
    feature_cols = [c for c in feature_cols if c in df.columns]

    X = df[feature_cols].values
    y = df['Penjualan'].values

    split_idx = int(len(df) * (1 - test_size))
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    scaler = None
    if scale:
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)
        X_test  = scaler.transform(X_test)

    return X_train, X_test, y_train, y_test, scaler, feature_cols


def prepare_data_classification(df: pd.DataFrame, target: str = 'Penjualan',
                                 test_size: float = 0.2, scale: bool = True):
    """
    Split data time-based untuk KLASIFIKASI.
    target = 'Penjualan' (multi-class 0/1/2/3)
           = 'penjualan_binary' (binary 0=rendah, 1=tinggi)
    Returns: X_train, X_test, y_train, y_test, scaler, feature_cols
    """
    feature_cols = get_feature_columns()
    feature_cols = [c for c in feature_cols if c in df.columns]

    X = df[feature_cols].values
    y = df[target].values.astype(int)

    split_idx = int(len(df) * (1 - test_size))
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    scaler = None
    if scale:
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)
        X_test  = scaler.transform(X_test)

    return X_train, X_test, y_train, y_test, scaler, feature_cols
