import pandas as pd
import os
from config import get_engine

# Pastikan path CSV selalu relatif ke lokasi file script ini
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def run_dimensi():
    print(">>> Mulai ETL Dimensi...")
    engine = get_engine()

    # -------------------------
    # 1. BACA CSV
    # -------------------------
    df_waktu   = pd.read_csv(os.path.join(BASE_DIR, 'dim_waktu_clean.csv'), sep=';')
    df_nasabah = pd.read_csv(os.path.join(BASE_DIR, 'nasabah_crm.csv'), sep=';')
    df_nasabah.columns = df_nasabah.columns.str.strip()
    print("Kolom nasabah:", df_nasabah.columns.tolist())

    df_merchant = pd.read_csv(os.path.join(BASE_DIR, 'merchant_mms.csv'), sep=';')
    df_trx      = pd.read_csv(os.path.join(BASE_DIR, 'transaksi_raw.csv'), sep=';')

    # -------------------------
    # 2. DIMENSI WAKTU
    # -------------------------
    df_dim_waktu = df_waktu.copy()
    print(f"    dim_waktu      : {len(df_dim_waktu)} baris")

    # -------------------------
    # 3. DIMENSI NASABAH
    # -------------------------
    df_dim_nasabah = df_nasabah.copy()

    map_jk = {'M': 'L', 'Laki-laki': 'L', 'L': 'L', 'P': 'P', 'Female': 'P'}
    df_dim_nasabah['jenis_kelamin'] = df_dim_nasabah['jenis_kelamin'].map(map_jk).fillna('U')

    df_dim_nasabah['tanggal_lahir'] = pd.to_datetime(
        df_dim_nasabah['tanggal_lahir'], dayfirst=True, errors='coerce'
    ).dt.date

    df_dim_nasabah['segmen_nasabah'] = (
        df_dim_nasabah['segmen_nasabah']
        .fillna('Reguler')
        .replace({'RETAIL': 'Reguler', 'prio': 'Prioritas'})
    )

    df_dim_nasabah.insert(0, 'nasabah_id', range(1, len(df_dim_nasabah) + 1))

    # Row Unknown — sesuaikan jumlah kolom: nasabah_id, nasabah_code, nama_lengkap, jenis_kelamin, tanggal_lahir, segmen_nasabah
    unknown_nasabah = {
        'nasabah_id'    : 0,
        'nasabah_code'  : 'UNKNOWN',
        'nama_lengkap'  : 'Unknown',
        'jenis_kelamin' : 'U',
        'tanggal_lahir' : None,
        'segmen_nasabah': 'Unknown',
    }
    df_dim_nasabah = pd.concat(
        [df_dim_nasabah, pd.DataFrame([unknown_nasabah])],
        ignore_index=True
    )
    print(f"    dim_nasabah    : {len(df_dim_nasabah)} baris (termasuk Unknown)")

    # -------------------------
    # 4. DIMENSI MERCHANT
    # -------------------------
    df_dim_merchant = df_merchant.copy()
    df_dim_merchant['kategori'] = df_dim_merchant['kategori'].fillna('Unknown')
    df_dim_merchant.insert(0, 'merchant_id', range(1, len(df_dim_merchant) + 1))

    unknown_merchant = {
        'merchant_id'   : 0,
        'merchant_code' : 'MCH-UNKNOWN',
        'nama_merchant' : 'Unknown Merchant',
        'kategori'      : 'Unknown',
    }
    df_dim_merchant = pd.concat(
        [df_dim_merchant, pd.DataFrame([unknown_merchant])],
        ignore_index=True
    )
    print(f"    dim_merchant   : {len(df_dim_merchant)} baris (termasuk Unknown)")

    # -------------------------
    # 5. DIMENSI CHANNEL
    # -------------------------
    map_channel = {
        'BIFAST' : 'BI_FAST',
        'LIVIN'  : 'LIVIN',
        'livin'  : 'LIVIN',
    }
    channels = (
        df_trx['channel']
        .dropna()
        .str.strip()
        .str.upper()
        .replace({'BIFAST': 'BI_FAST'})   # .replace() works on Series values
        .unique()
    )
    df_dim_channel = pd.DataFrame({
        'nama_channel' : channels,
        'jenis_channel': 'Digital',
    })
    df_dim_channel.insert(0, 'channel_id', range(1, len(df_dim_channel) + 1))

    unknown_channel = {'channel_id': 0, 'nama_channel': 'UNKNOWN', 'jenis_channel': 'Unknown'}
    df_dim_channel = pd.concat(
        [df_dim_channel, pd.DataFrame([unknown_channel])],
        ignore_index=True
    )
    print(f"    dim_channel    : {len(df_dim_channel)} baris (termasuk Unknown)")

    # -------------------------
    # 6. DIMENSI WILAYAH
    # -------------------------
    map_kota = {'BDG': 'Bandung', 'Jkt Sel': 'Jakarta Selatan', 'SBY': 'Surabaya'}
    map_prov = {
        'Bandung'          : 'Jawa Barat',
        'Jakarta Selatan'  : 'DKI Jakarta',
        'Surabaya'         : 'Jawa Timur',
    }

    kotas = df_trx['kota'].dropna().str.strip().replace(map_kota).unique()
    df_dim_wilayah = pd.DataFrame({'kota': kotas})
    df_dim_wilayah['provinsi'] = df_dim_wilayah['kota'].map(map_prov).fillna('Unknown')
    df_dim_wilayah['region']   = 'Indonesia'
    df_dim_wilayah.insert(0, 'wilayah_id', range(1, len(df_dim_wilayah) + 1))

    unknown_wilayah = {'wilayah_id': 0, 'kota': 'Unknown', 'provinsi': 'Unknown', 'region': 'Unknown'}
    df_dim_wilayah = pd.concat(
        [df_dim_wilayah, pd.DataFrame([unknown_wilayah])],
        ignore_index=True
    )
    print(f"    dim_wilayah    : {len(df_dim_wilayah)} baris (termasuk Unknown)")

    # -------------------------
    # 7. LOAD KE POSTGRESQL
    # -------------------------
    print("    -> Insert ke database...")
    df_dim_waktu.to_sql   ('dim_waktu',    engine, if_exists='append', index=False)
    df_dim_nasabah.to_sql ('dim_nasabah',  engine, if_exists='append', index=False)
    df_dim_merchant.to_sql('dim_merchant', engine, if_exists='append', index=False)
    df_dim_channel.to_sql ('dim_channel',  engine, if_exists='append', index=False)
    df_dim_wilayah.to_sql ('dim_wilayah',  engine, if_exists='append', index=False)

    print(">>> Dimensi SELESAI!")


# ← INI YANG BIKIN FUNGSI DIPANGGIL SAAT SCRIPT DIJALANKAN
if __name__ == '__main__':
    run_dimensi()