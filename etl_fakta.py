# etl_fakta.py
# Proses ETL untuk tabel fakta dan pembuatan materialized view dashboard.
#
# Source data  : transaksi_raw.csv  +  surrogate key dari tabel dimensi (sudah di-load)
# Target       : PostgreSQL — tabel fact_transaksi
#                              materialized view mvw_dashboard_transaksi (untuk Looker Studio)
#
# Fakta diisi SETELAH semua dimensi ada karena tabel fakta ber-FK ke semua dimensi.
# Setiap dimensi yang gagal di-join akan di-fallback ke id=0 (baris Unknown).
#
# Mode load:
#   - run_fakta()             -> FULL LOAD  (insert semua baris, dipakai setelah TRUNCATE)
#   - run_fakta_incremental() -> INCREMENTAL LOAD (hanya insert transaksi dengan
#                                  waktu_id > MAX(waktu_id) yang sudah ada di fact_transaksi —
#                                  dipakai sebagai watermark batch terakhir)

import pandas as pd
import os
from config import get_engine, DATA_DIR
from etl_dimensi import _read_source_csv
from sqlalchemy import text


def _transform_fakta(engine):
    """EXTRACT + TRANSFORM + LOOKUP transaksi. Mengembalikan DataFrame siap insert
    (kolom sesuai DDL fact_transaksi, TANPA kolom fact_id)."""

    # -------------------------
    # 1. EXTRACT — BACA DATA
    # -------------------------
    # Transaksi mentah dari CSV (sumber utama tabel fakta) — wajib ada di DATA_DIR
    df_trx = _read_source_csv('transaksi_raw.csv')
    if df_trx is None:
        raise FileNotFoundError(f"transaksi_raw.csv tidak ditemukan di {DATA_DIR}")

    # Baca surrogate key dari dimensi yang sudah di-load ke DB.
    # Ini dipakai untuk lookup/join agar fakta menyimpan id bukan kode natural.
    db_nasabah  = pd.read_sql("SELECT nasabah_id, nasabah_code FROM dim_nasabah", engine)
    db_merchant = pd.read_sql("SELECT merchant_id, merchant_code FROM dim_merchant", engine)
    db_channel  = pd.read_sql("SELECT channel_id, nama_channel FROM dim_channel", engine)
    db_wilayah  = pd.read_sql("SELECT wilayah_id, kota FROM dim_wilayah", engine)

    # -------------------------
    # 2. TRANSFORM — BERSIHKAN DATA TRANSAKSI
    # -------------------------
    # Hapus duplikat berdasarkan trx_id agar setiap transaksi hanya muncul sekali
    df_fact = df_trx.drop_duplicates(subset=['trx_id']).copy()

    # Bersihkan kolom nominal: hapus titik ribuan (1.000.000 → 1000000),
    # ganti koma desimal dengan titik, lalu konversi ke angka.
    df_fact['nominal'] = (
        df_fact['nominal']
        .astype(str)
        .str.strip()
        .str.replace('.', '', regex=False)   # hilangkan separator ribuan
        .str.replace(',', '.', regex=False)  # ganti koma desimal ke titik
    )
    df_fact['nominal']     = pd.to_numeric(df_fact['nominal'],     errors='coerce').fillna(0)
    df_fact['biaya_admin'] = pd.to_numeric(df_fact['biaya_admin'], errors='coerce').fillna(0)

    # Buang baris dengan nominal negatif (data tidak valid)
    df_fact = df_fact[df_fact['nominal'] >= 0]

    # Buat waktu_id bertipe integer format YYYYMMDD (misal: 20240115)
    # agar bisa di-FK ke dim_waktu.waktu_id yang pakai format yang sama.
    df_fact['waktu_id'] = (
        pd.to_datetime(df_fact['tgl_transaksi'], dayfirst=True, errors='coerce')
        .dt.strftime('%Y%m%d')
    )
    baris_invalid = df_fact['waktu_id'].isna().sum()
    if baris_invalid > 0:
        print(f"    [WARN] {baris_invalid} baris punya tanggal tidak valid, akan di-drop")
    df_fact = df_fact.dropna(subset=['waktu_id'])
    df_fact['waktu_id'] = df_fact['waktu_id'].astype(int)

    # Normalisasi nama channel dengan .map() — lebih aman dari .replace() karena
    # .replace() pada Series tidak selalu handle semua case (BIFAST tidak ter-handle).
    map_channel = {
        'ATM'     : 'ATM',
        'BI_FAST' : 'BI_FAST',
        'BIFAST'  : 'BI_FAST',   # alias lama dari data source
        'QRIS'    : 'QRIS',
        'ATM_LINK': 'ATM_LINK',
        'LIVIN'   : 'LIVIN',
    }
    df_fact['channel_bersih'] = (
        df_fact['channel']
        .str.strip()
        .str.upper()
        .map(map_channel)       # nilai tidak ada di map → NaN → diisi 'UNKNOWN'
        .fillna('UNKNOWN')
    )

    # Normalisasi nama kota dari singkatan/variasi ke nama lengkap baku
    map_kota = {'BDG': 'Bandung', 'Jkt Sel': 'Jakarta Selatan', 'SBY': 'Surabaya'}
    df_fact['kota_bersih'] = (
        df_fact['kota']
        .str.strip()
        .replace(map_kota)
        .fillna('Unknown')
    )

    # Isi nilai null di natural key dengan kode Unknown agar join ke dimensi
    # selalu berhasil dan mengarah ke baris fallback id=0
    df_fact['merchant_code'] = df_fact['merchant_code'].fillna('MCH-UNKNOWN')
    df_fact['nasabah_code']  = df_fact['nasabah_code'].fillna('UNKNOWN')

    # -------------------------
    # 3. LOOKUP / JOIN — TUKAR NATURAL KEY → SURROGATE KEY
    # -------------------------
    # Setiap join menggunakan natural key (kode dari source) untuk mendapatkan
    # surrogate key integer yang akan disimpan di tabel fakta (prinsip star schema).
    # how='left' menjaga semua baris fakta tetap ada meski join gagal (hasilnya NaN).
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
        suffixes=('', '_db')   # hindari collision nama kolom 'kota'
    )

    # -------------------------
    # 4. FINALISASI — SIAPKAN KOLOM FINAL
    # -------------------------
    # Rename agar nama kolom sesuai DDL tabel fact_transaksi di database
    df_fact = df_fact.rename(columns={'nominal': 'nominal_transaksi'})

    # Ganti NaN dari join yang gagal dengan 0 (id Unknown) — pastikan tipe int
    kolom_id = ['nasabah_id', 'merchant_id', 'channel_id', 'wilayah_id']
    df_fact[kolom_id] = df_fact[kolom_id].fillna(0).astype(int)

    # Validasi: pastikan waktu_id benar-benar ada di dim_waktu.
    # FK violation akan membuat to_sql gagal total jika ada waktu_id yang tidak valid.
    waktu_valid = pd.read_sql("SELECT waktu_id FROM dim_waktu", engine)['waktu_id'].tolist()
    invalid_waktu = ~df_fact['waktu_id'].isin(waktu_valid)
    if invalid_waktu.sum() > 0:
        print(f"    [WARN] {invalid_waktu.sum()} baris di-drop karena waktu_id tidak ada di dim_waktu:")
        print(df_fact.loc[invalid_waktu, ['trx_id', 'tgl_transaksi', 'waktu_id']])
        df_fact = df_fact[~invalid_waktu]

    # Pilih hanya kolom yang dibutuhkan tabel fakta (buang semua kolom intermediate)
    kolom_final = [
        'waktu_id', 'nasabah_id', 'channel_id',
        'wilayah_id', 'merchant_id', 'nominal_transaksi', 'biaya_admin'
    ]
    return df_fact[kolom_final]


def run_fakta():
    """FULL LOAD — insert semua baris fakta (dipakai setelah TRUNCATE di main.py)."""
    print(">>> Mulai ETL Fakta (Full Load)...")
    engine = get_engine()

    df_final = _transform_fakta(engine)

    # Buat surrogate key fact_id mulai dari 1 di posisi kolom pertama
    df_final = df_final.copy()
    df_final.insert(0, 'fact_id', range(1, len(df_final) + 1))
    print(f"    Total baris fakta siap insert: {len(df_final)}")

    print("    -> Insert ke tabel fakta...")
    df_final.to_sql('fact_transaksi', engine, if_exists='append', index=False)
    print(">>> Fakta SELESAI!")


def run_fakta_incremental():
    """INCREMENTAL LOAD — hanya insert transaksi baru berdasarkan watermark
    MAX(waktu_id) yang sudah ada di fact_transaksi. Tidak melakukan TRUNCATE;
    fact_id baris baru melanjutkan dari MAX(fact_id) di DB.

    Catatan: pendekatan watermark tanggal ini berarti transaksi yang "telat masuk"
    (late-arriving) untuk tanggal yang sudah pernah di-load tidak akan ter-capture.
    """
    print(">>> Mulai ETL Fakta (Incremental Load)...")
    engine = get_engine()

    df_final = _transform_fakta(engine)

    row = pd.read_sql(
        "SELECT COALESCE(MAX(waktu_id), 0) AS max_waktu, COALESCE(MAX(fact_id), 0) AS max_fact "
        "FROM fact_transaksi", engine
    ).iloc[0]
    watermark_waktu = int(row['max_waktu'])
    max_fact_id     = int(row['max_fact'])
    print(f"    Watermark waktu_id saat ini: {watermark_waktu}")

    df_baru = df_final[df_final['waktu_id'] > watermark_waktu].copy()
    if df_baru.empty:
        print("    Tidak ada transaksi baru (waktu_id <= watermark). Selesai.")
        return

    df_baru.insert(0, 'fact_id', range(max_fact_id + 1, max_fact_id + 1 + len(df_baru)))
    print(f"    Total baris fakta baru siap insert: {len(df_baru)}")

    print("    -> Insert ke tabel fakta...")
    df_baru.to_sql('fact_transaksi', engine, if_exists='append', index=False)
    print(">>> Fakta (Incremental) SELESAI!")


def create_materialized_view():
    """
    Buat materialized view denormalisasi untuk konsumsi Looker Studio.

    View ini menggabungkan fact_transaksi dengan semua dimensi sehingga
    Looker Studio bisa query langsung tanpa JOIN kompleks.
    Materialized view di-refresh setiap kali pipeline ETL jalan (DROP + CREATE).
    """
    print(">>> Membuat Materialized View untuk Looker Studio di Aiven...")
    engine = get_engine()

    # DROP dulu agar bisa dibuat ulang dengan data terbaru setiap pipeline jalan.
    # CREATE ... AS SELECT: satu baris per transaksi + semua atribut dimensi denormalisasi.
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

    # AUTOCOMMIT diperlukan karena CREATE MATERIALIZED VIEW tidak bisa dijalankan
    # di dalam transaksi eksplisit (PostgreSQL akan error jika pakai BEGIN/COMMIT biasa).
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text(query))
        print("✓ Materialized View berhasil dibuat di Aiven!")


if __name__ == '__main__':
    run_fakta()
