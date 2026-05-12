# etl_fakta.py
import pandas as pd
import os
from config import get_engine
from sqlalchemy import text


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def run_fakta():
    print(">>> Mulai ETL Fakta...")
    engine = get_engine()

    # -------------------------
    # 1. BACA DATA
    # -------------------------
    df_trx = pd.read_csv(os.path.join(BASE_DIR, 'transaksi_raw.csv'), sep=';')

    db_nasabah  = pd.read_sql("SELECT nasabah_id, nasabah_code FROM dim_nasabah", engine)
    db_merchant = pd.read_sql("SELECT merchant_id, merchant_code FROM dim_merchant", engine)
    db_channel  = pd.read_sql("SELECT channel_id, nama_channel FROM dim_channel", engine)
    db_wilayah  = pd.read_sql("SELECT wilayah_id, kota FROM dim_wilayah", engine)

    # -------------------------
    # 2. TRANSFORM
    # -------------------------
    df_fact = df_trx.drop_duplicates(subset=['trx_id']).copy()

    # FIX: bersihkan nominal dulu sebelum to_numeric (jaga-jaga ada titik ribuan/spasi)
    df_fact['nominal'] = (
        df_fact['nominal']
        .astype(str)
        .str.strip()
        .str.replace('.', '', regex=False)
        .str.replace(',', '.', regex=False)
    )
    df_fact['nominal']     = pd.to_numeric(df_fact['nominal'],     errors='coerce').fillna(0)
    df_fact['biaya_admin'] = pd.to_numeric(df_fact['biaya_admin'], errors='coerce').fillna(0)
    df_fact = df_fact[df_fact['nominal'] >= 0]

    # Waktu ID — handle NaT sebelum astype int
    df_fact['waktu_id'] = (
        pd.to_datetime(df_fact['tgl_transaksi'], dayfirst=True, errors='coerce')
        .dt.strftime('%Y%m%d')
    )
    baris_invalid = df_fact['waktu_id'].isna().sum()
    if baris_invalid > 0:
        print(f"    [WARN] {baris_invalid} baris punya tanggal tidak valid, akan di-drop")
    df_fact = df_fact.dropna(subset=['waktu_id'])
    df_fact['waktu_id'] = df_fact['waktu_id'].astype(int)

    # FIX: pakai .map() bukan .replace() supaya BIFAST → BI_FAST benar-benar jalan
    map_channel = {
        'ATM'     : 'ATM',
        'BI_FAST' : 'BI_FAST',
        'BIFAST'  : 'BI_FAST',   # ← ini yang sebelumnya tidak ke-handle
        'QRIS'    : 'QRIS',
        'ATM_LINK': 'ATM_LINK',
        'LIVIN'   : 'LIVIN',
    }
    df_fact['channel_bersih'] = (
        df_fact['channel']
        .str.strip()
        .str.upper()
        .map(map_channel)          # ← .map() bukan .replace()
        .fillna('UNKNOWN')
    )

    map_kota = {'BDG': 'Bandung', 'Jkt Sel': 'Jakarta Selatan', 'SBY': 'Surabaya'}
    df_fact['kota_bersih'] = (
        df_fact['kota']
        .str.strip()
        .replace(map_kota)
        .fillna('Unknown')
    )

    df_fact['merchant_code'] = df_fact['merchant_code'].fillna('MCH-UNKNOWN')
    df_fact['nasabah_code']  = df_fact['nasabah_code'].fillna('UNKNOWN')

    # -------------------------
    # 3. LOOKUP / JOIN
    # -------------------------
    df_fact = df_fact.merge(db_nasabah,  on='nasabah_code',  how='left')
    df_fact = df_fact.merge(db_merchant, on='merchant_code', how='left')
    df_fact = df_fact.merge(
        db_channel,
        left_on='channel_bersih', right_on='nama_channel',
        how='left'
    )
    df_fact = df_fact.merge(
        db_wilayah,
        left_on='kota_bersih', right_on='kota',
        how='left',
        suffixes=('', '_db')
    )

    # -------------------------
    # 4. FINALISASI
    # -------------------------
    # Rename nominal → nominal_transaksi (kolom di CSV memang 'nominal')
    df_fact = df_fact.rename(columns={'nominal': 'nominal_transaksi'})

    # Gagal join → fallback ke ID 0 (Unknown)
    kolom_id = ['nasabah_id', 'merchant_id', 'channel_id', 'wilayah_id']
    df_fact[kolom_id] = df_fact[kolom_id].fillna(0).astype(int)

    # Validasi waktu_id ada di dim_waktu — hindari FK violation
    waktu_valid = pd.read_sql("SELECT waktu_id FROM dim_waktu", engine)['waktu_id'].tolist()
    invalid_waktu = ~df_fact['waktu_id'].isin(waktu_valid)
    if invalid_waktu.sum() > 0:
        print(f"    [WARN] {invalid_waktu.sum()} baris di-drop karena waktu_id tidak ada di dim_waktu:")
        print(df_fact.loc[invalid_waktu, ['trx_id', 'tgl_transaksi', 'waktu_id']])
        df_fact = df_fact[~invalid_waktu]

    df_fact.insert(0, 'fact_id', range(1, len(df_fact) + 1))

    kolom_final = [
        'fact_id', 'waktu_id', 'nasabah_id', 'channel_id',
        'wilayah_id', 'merchant_id', 'nominal_transaksi', 'biaya_admin'
    ]
    df_final = df_fact[kolom_final]
    print(f"    Total baris fakta siap insert: {len(df_final)}")

    # -------------------------
    # 5. LOAD KE DATABASE
    # -------------------------
    print("    -> Insert ke tabel fakta...")
    df_final.to_sql('fact_transaksi', engine, if_exists='append', index=False)
    print(">>> Fakta SELESAI!")

def create_materialized_view():
    print(">>> Membuat Materialized View untuk Looker Studio di Aiven...")
    engine = get_engine()
    
    # Query SQL yang tadi
    query = """
    DROP MATERIALIZED VIEW IF EXISTS mvw_dashboard_transaksi;
    CREATE MATERIALIZED VIEW mvw_dashboard_transaksi AS
    SELECT 
        f.fact_id,
        w.tanggal,
        w.bulan,
        w.tahun,
        n.nama_lengkap,
        n.segmen_nasabah,
        n.jenis_kelamin,
        c.nama_channel,
        wil.kota,
        wil.provinsi,
        m.nama_merchant,
        m.kategori AS kategori_merchant,
        f.nominal_transaksi,
        f.biaya_admin
    FROM fact_transaksi f
    LEFT JOIN dim_waktu w ON f.waktu_id = w.waktu_id
    LEFT JOIN dim_nasabah n ON f.nasabah_id = n.nasabah_id
    LEFT JOIN dim_channel c ON f.channel_id = c.channel_id
    LEFT JOIN dim_wilayah wil ON f.wilayah_id = wil.wilayah_id
    LEFT JOIN dim_merchant m ON f.merchant_id = m.merchant_id;
    """
    
    with engine.connect() as conn:
        # Pake execution_options(isolation_level="AUTOCOMMIT") 
        # biar gak perlu manual commit
        conn.execute(text(query))
        print("✓ Materialized View berhasil dibuat di Aiven!")

if __name__ == '__main__':
    run_fakta()