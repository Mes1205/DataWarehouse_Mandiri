# etl_dimensi.py
# Proses ETL untuk semua tabel dimensi pada skema bintang (star schema).
#
# Source data  : file CSV lokal (CRM, MMS, dan data transaksi mentah)
# Target       : PostgreSQL — tabel dim_waktu, dim_nasabah, dim_merchant,
#                              dim_channel, dim_wilayah
#
# Setiap dimensi diberi satu baris "Unknown" (id=0) sebagai fallback
# ketika tabel fakta tidak berhasil join ke baris yang valid.
#
# Mode load:
#   - run_dimensi()             -> FULL LOAD  (insert semua baris, dipakai setelah TRUNCATE)
#   - run_dimensi_incremental() -> INCREMENTAL LOAD (hanya insert baris dengan
#                                   natural key yang belum ada di DB; surrogate id
#                                   melanjutkan dari MAX id yang sudah ada)

import pandas as pd
import os
from config import get_engine, DATA_DIR


def _read_source_csv(filename):
    """Baca CSV dari DATA_DIR. Return None jika file tidak ada — supaya satu
    folder DATA_DIR boleh hanya berisi sebagian file (mis. cuma nasabah,
    merchant, transaksi). Separator ';' atau ',' dideteksi otomatis dari header."""
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        header = f.readline()
    sep = ';' if header.count(';') >= header.count(',') else ','
    return pd.read_csv(path, sep=sep)


def _transform_dimensi():
    """EXTRACT + TRANSFORM dimensi dari CSV yang tersedia di DATA_DIR.
    Mengembalikan dict of DataFrame siap insert (sudah termasuk baris 'Unknown'
    id=0 untuk dimensi yang punya fallback). Dimensi yang file sumbernya tidak
    ada di DATA_DIR akan bernilai None (dilewati oleh run_dimensi*)."""

    # -------------------------
    # 1. EXTRACT — BACA CSV (yang ada saja)
    # -------------------------
    # dim_waktu_clean.csv  : kalender harian yang sudah dibersihkan (pre-generated)
    # nasabah_crm.csv      : data nasabah dari sistem CRM
    # merchant_mms.csv     : data merchant dari sistem MMS
    # transaksi_raw.csv    : transaksi mentah — wajib ada, dipakai untuk ekstrak channel & kota unik
    df_waktu    = _read_source_csv('dim_waktu_clean.csv')
    df_nasabah  = _read_source_csv('nasabah_crm.csv')
    df_merchant = _read_source_csv('merchant_mms.csv')
    df_trx      = _read_source_csv('transaksi_raw.csv')

    if df_trx is None:
        raise FileNotFoundError(
            f"transaksi_raw.csv tidak ditemukan di {DATA_DIR} — file ini wajib ada "
            "(dipakai untuk ekstrak dim_channel & dim_wilayah)."
        )

    if df_nasabah is not None:
        df_nasabah.columns = df_nasabah.columns.str.strip()  # hilangkan spasi di nama kolom
        print("Kolom nasabah:", df_nasabah.columns.tolist())

    # -------------------------
    # 2. TRANSFORM — DIMENSI WAKTU
    # -------------------------
    # Tidak perlu transformasi tambahan; CSV sudah bersih dan strukturnya sesuai DDL.
    if df_waktu is not None:
        df_dim_waktu = df_waktu.copy()
        print(f"    dim_waktu      : {len(df_dim_waktu)} baris")
    else:
        df_dim_waktu = None
        print("    dim_waktu      : dim_waktu_clean.csv tidak ditemukan, dilewati")

    # -------------------------
    # 3. TRANSFORM — DIMENSI NASABAH
    # -------------------------
    if df_nasabah is not None:
        df_dim_nasabah = df_nasabah.copy()

        # Standarisasi kode jenis kelamin dari berbagai format sumber menjadi L/P/U
        map_jk = {'M': 'L', 'Laki-laki': 'L', 'L': 'L', 'P': 'P', 'Female': 'P'}
        df_dim_nasabah['jenis_kelamin'] = df_dim_nasabah['jenis_kelamin'].map(map_jk).fillna('U')

        # Parse tanggal lahir — dayfirst=True karena format CSV dd/mm/yyyy
        df_dim_nasabah['tanggal_lahir'] = pd.to_datetime(
            df_dim_nasabah['tanggal_lahir'], dayfirst=True, errors='coerce'
        ).dt.date

        # Standarisasi label segmen nasabah ke nilai baku
        df_dim_nasabah['segmen_nasabah'] = (
            df_dim_nasabah['segmen_nasabah']
            .fillna('Reguler')
            .replace({'RETAIL': 'Reguler', 'prio': 'Prioritas'})
        )

        # Buat surrogate key nasabah_id mulai dari 1
        df_dim_nasabah.insert(0, 'nasabah_id', range(1, len(df_dim_nasabah) + 1))

        # Tambah baris Unknown (id=0) sebagai fallback jika nasabah_code di transaksi tidak dikenal
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
    else:
        df_dim_nasabah = None
        print("    dim_nasabah    : nasabah_crm.csv tidak ditemukan, dilewati")

    # -------------------------
    # 4. TRANSFORM — DIMENSI MERCHANT
    # -------------------------
    if df_merchant is not None:
        df_dim_merchant = df_merchant.copy()
        df_dim_merchant['kategori'] = df_dim_merchant['kategori'].fillna('Unknown')

        # Surrogate key merchant_id mulai dari 1
        df_dim_merchant.insert(0, 'merchant_id', range(1, len(df_dim_merchant) + 1))

        # Fallback merchant jika merchant_code tidak ditemukan saat join di tabel fakta
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
    else:
        df_dim_merchant = None
        print("    dim_merchant   : merchant_mms.csv tidak ditemukan, dilewati")

    # -------------------------
    # 5. TRANSFORM — DIMENSI CHANNEL
    # -------------------------
    # Ekstrak nilai channel unik langsung dari data transaksi mentah,
    # lalu normalisasi nama (uppercase, 'BIFAST' → 'BI_FAST').
    channels = (
        df_trx['channel']
        .dropna()
        .str.strip()
        .str.upper()
        .replace({'BIFAST': 'BI_FAST'})
        .unique()
    )
    df_dim_channel = pd.DataFrame({
        'nama_channel' : channels,
        'jenis_channel': 'Digital',   # semua channel saat ini dikategorikan Digital
    })
    df_dim_channel.insert(0, 'channel_id', range(1, len(df_dim_channel) + 1))

    # Fallback channel Unknown (id=0)
    unknown_channel = {'channel_id': 0, 'nama_channel': 'UNKNOWN', 'jenis_channel': 'Unknown'}
    df_dim_channel = pd.concat(
        [df_dim_channel, pd.DataFrame([unknown_channel])],
        ignore_index=True
    )
    print(f"    dim_channel    : {len(df_dim_channel)} baris (termasuk Unknown)")

    # -------------------------
    # 6. TRANSFORM — DIMENSI WILAYAH
    # -------------------------
    # Kota juga diekstrak dari transaksi mentah, lalu diperkaya dengan provinsi.
    map_kota = {'BDG': 'Bandung', 'Jkt Sel': 'Jakarta Selatan', 'SBY': 'Surabaya'}
    map_prov = {
        'Bandung'          : 'Jawa Barat',
        'Jakarta Selatan'  : 'DKI Jakarta',
        'Surabaya'         : 'Jawa Timur',
    }

    kotas = df_trx['kota'].dropna().str.strip().replace(map_kota).unique()
    df_dim_wilayah = pd.DataFrame({'kota': kotas})
    df_dim_wilayah['provinsi'] = df_dim_wilayah['kota'].map(map_prov).fillna('Unknown')
    df_dim_wilayah['region']   = 'Indonesia'   # semua data saat ini dari Indonesia
    df_dim_wilayah.insert(0, 'wilayah_id', range(1, len(df_dim_wilayah) + 1))

    # Fallback wilayah Unknown (id=0)
    unknown_wilayah = {'wilayah_id': 0, 'kota': 'Unknown', 'provinsi': 'Unknown', 'region': 'Unknown'}
    df_dim_wilayah = pd.concat(
        [df_dim_wilayah, pd.DataFrame([unknown_wilayah])],
        ignore_index=True
    )
    print(f"    dim_wilayah    : {len(df_dim_wilayah)} baris (termasuk Unknown)")

    return {
        'dim_waktu'   : df_dim_waktu,
        'dim_nasabah' : df_dim_nasabah,
        'dim_merchant': df_dim_merchant,
        'dim_channel' : df_dim_channel,
        'dim_wilayah' : df_dim_wilayah,
    }


def run_dimensi():
    """FULL LOAD — insert semua baris dimensi (dipakai setelah TRUNCATE di main.py)."""
    print(">>> Mulai ETL Dimensi (Full Load)...")
    engine = get_engine()

    dims = _transform_dimensi()

    # if_exists='append' karena tabel sudah di-truncate di main.py sebelum ETL jalan.
    # Urutan insert tidak kritis di sini karena dimensi tidak saling ber-FK.
    # Dimensi yang None (file sumber tidak ada di DATA_DIR) dilewati -> tabel tetap kosong.
    print("    -> Insert ke database...")
    for table, df in dims.items():
        if df is None:
            print(f"    {table:<12} : dilewati (tidak ada data sumber)")
            continue
        df.to_sql(table, engine, if_exists='append', index=False)

    print(">>> Dimensi SELESAI!")


def _append_new_rows(df, engine, table, id_col, key_col):
    """Insert hanya baris yang natural key-nya (key_col) belum ada di tabel.
    Surrogate key (id_col) baris baru melanjutkan dari MAX(id_col) di DB.
    Khusus dim_waktu, id_col == key_col (waktu_id sudah natural), jadi tidak di-reassign."""
    existing = pd.read_sql(f"SELECT {key_col} FROM {table}", engine)[key_col]
    df_new = df[~df[key_col].isin(existing)].copy()

    if df_new.empty:
        print(f"    {table:<12} : tidak ada data baru")
        return

    if id_col != key_col:
        max_id = pd.read_sql(f"SELECT COALESCE(MAX({id_col}), 0) AS m FROM {table}", engine)['m'][0]
        df_new[id_col] = range(int(max_id) + 1, int(max_id) + 1 + len(df_new))

    df_new.to_sql(table, engine, if_exists='append', index=False)
    print(f"    {table:<12} : +{len(df_new)} baris baru")


def run_dimensi_incremental():
    """INCREMENTAL LOAD — hanya insert baris dimensi dengan natural key baru.
    Tidak melakukan TRUNCATE; aman dijalankan berulang kali (idempotent)."""
    print(">>> Mulai ETL Dimensi (Incremental Load)...")
    engine = get_engine()

    dims = _transform_dimensi()

    # (id_col, key_col) — key_col adalah natural key untuk deteksi baris baru
    mapping = {
        'dim_waktu'   : ('waktu_id',    'waktu_id'),
        'dim_nasabah' : ('nasabah_id',  'nasabah_code'),
        'dim_merchant': ('merchant_id', 'merchant_code'),
        'dim_channel' : ('channel_id',  'nama_channel'),
        'dim_wilayah' : ('wilayah_id',  'kota'),
    }

    print("    -> Cek & insert data baru...")
    for table, (id_col, key_col) in mapping.items():
        if dims[table] is None:
            print(f"    {table:<12} : dilewati (tidak ada data sumber)")
            continue
        _append_new_rows(dims[table], engine, table, id_col, key_col)

    print(">>> Dimensi (Incremental) SELESAI!")


if __name__ == '__main__':
    run_dimensi()
