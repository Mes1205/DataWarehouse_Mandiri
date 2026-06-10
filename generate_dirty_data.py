# generate_dirty_data.py
# Generator data dummy "kotor" untuk uji coba pipeline ETL Data Warehouse Mandiri.
#
# Tujuan: membuat dataset baru (nasabah_crm, merchant_mms, transaksi_raw, dim_waktu_clean)
# yang mengandung missing value & inkonsistensi format SEPERTI data asli, tapi tetap
# bisa diolah aman oleh etl_dimensi.py & etl_fakta.py (semua jenis "kotor" di sini
# sudah ada penanganannya di kode ETL: fillna, mapping, drop duplicate, drop invalid).
#
# Output: data/generate1/*.csv (sep=';', sama seperti CSV sumber asli)

import os
import random
from datetime import date, timedelta

import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'data', 'generate1')

SEED = 42
N_NASABAH = 3000
N_MERCHANT = 3000
N_TRANSAKSI = 15000

WAKTU_START = date(2025, 1, 1)
WAKTU_END = date(2026, 12, 31)

random.seed(SEED)

FIRST_NAMES = ['Andi', 'Budi', 'Citra', 'Dewi', 'Eka', 'Fajar', 'Gita', 'Hadi',
               'Indah', 'Joko', 'Kartika', 'Lutfi', 'Maya', 'Nanda', 'Oki',
               'Putri', 'Rizal', 'Sari', 'Tono', 'Umi', 'Vina', 'Wawan', 'Yuni', 'Zaki']
LAST_NAMES = ['Saputra', 'Wijaya', 'Lestari', 'Pratama', 'Santoso', 'Hidayat',
              'Maharani', 'Kusuma', 'Permata', 'Hakim', 'Utami', 'Setiawan']

MERCHANT_PREFIX = ['Toko', 'Warung', 'Resto', 'Cafe', 'Apotek', 'Bengkel', 'Minimarket', 'Klinik']
MERCHANT_SUFFIX = ['Mandiri', 'Sejahtera', 'Jaya', 'Makmur', 'Berkah', 'Sentosa', 'Abadi', 'Indah']

# Variasi "kotor" — semua sudah ditangani oleh map_jk / fillna di etl_dimensi.py
JK_VALUES = ['L', 'P', 'M', 'Laki-laki', 'Female', 'Pria', 'Wanita', '']

# Sudah ditangani fillna('Reguler') + replace({'RETAIL':'Reguler','prio':'Prioritas'})
SEGMEN_VALUES = ['Reguler', 'Prioritas', 'RETAIL', 'prio', 'Private', '']

# Sudah ditangani fillna('Unknown') di dim_merchant
KATEGORI_VALUES = ['Retail', 'F&B', 'Food & Beverage', 'Health', 'Kesehatan',
                    'Market', 'Electronics', '']

# Sudah ditangani map_channel + fillna('UNKNOWN') di etl_fakta.py
CHANNEL_VALUES = ['ATM', 'BI_FAST', 'BIFAST', 'bifast', 'QRIS', 'qris',
                   'ATM_LINK', 'LIVIN', 'livin', '', 'TRANSFER']

# Sudah ditangani map_kota + fillna('Unknown') di etl_fakta.py
# 'Medan'/'Yogyakarta' tidak ada di map_prov -> jadi provinsi 'Unknown' (aman, sudah di-handle)
KOTA_VALUES = ['BDG', 'Bandung', 'Jkt Sel', 'Jakarta Selatan', 'SBY', 'Surabaya',
                'Medan', 'Yogyakarta', '']


def random_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def gen_dim_waktu():
    rows = []
    d = WAKTU_START
    while d <= WAKTU_END:
        rows.append({
            'waktu_id': int(d.strftime('%Y%m%d')),
            'tanggal': d.isoformat(),
            'hari': d.strftime('%A'),
            'bulan': d.strftime('%B'),
            'tahun': d.year,
            'quarter': f"Q{(d.month - 1) // 3 + 1}",
        })
        d += timedelta(days=1)
    return pd.DataFrame(rows)


def gen_nasabah():
    rows = []
    for i in range(1, N_NASABAH + 1):
        nama = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        jk = random.choice(JK_VALUES)

        # ~5% tanggal lahir kosong, ~3% format invalid (tanggal tidak ada / 31/02)
        roll = random.random()
        if roll < 0.05:
            ttl = ''
        elif roll < 0.08:
            ttl = '31/02/1999'  # tanggal tidak valid -> jadi NaT (errors='coerce')
        else:
            ttl_date = random_date(date(1960, 1, 1), date(2005, 12, 31))
            ttl = ttl_date.strftime('%d/%m/%Y')  # format dd/mm/yyyy (dayfirst=True)

        segmen = random.choice(SEGMEN_VALUES)

        rows.append({
            'nasabah_code': f"N-{20000 + i}",
            'nama_lengkap': nama,
            'jenis_kelamin': jk,
            'tanggal_lahir': ttl,
            'segmen_nasabah': segmen,
        })
    return pd.DataFrame(rows)


def gen_merchant():
    rows = []
    for i in range(1, N_MERCHANT + 1):
        nama = f"{random.choice(MERCHANT_PREFIX)} {random.choice(MERCHANT_SUFFIX)} {i}"
        kategori = random.choice(KATEGORI_VALUES)
        rows.append({
            'merchant_code': f"MCH-{8000 + i}",
            'nama_merchant': nama,
            'kategori': kategori,
        })
    return pd.DataFrame(rows)


def fmt_nominal(value: int) -> str:
    """Format angka ke gaya Indonesia: titik ribuan, kadang koma desimal."""
    sign = '-' if value < 0 else ''
    value = abs(value)
    grouped = f"{value:,}".replace(',', '.')  # 1000000 -> 1.000.000
    if random.random() < 0.2:
        grouped += f",{random.randint(0, 99):02d}"  # tambahin desimal koma
    return sign + grouped


def gen_transaksi(nasabah_codes, merchant_codes):
    rows = []
    used_ids = []

    for i in range(1, N_TRANSAKSI + 1):
        trx_id = f"TRX-{400000 + i}"
        used_ids.append(trx_id)

        # Tanggal transaksi
        roll_date = random.random()
        if roll_date < 0.02:
            tgl = ''  # kosong -> baris di-drop oleh ETL (waktu_id NaN)
        elif roll_date < 0.04:
            tgl = '31-13-2026'  # bulan tidak valid -> NaT -> di-drop
        elif roll_date < 0.07:
            # tanggal valid tapi DI LUAR rentang dim_waktu -> di-drop saat validasi FK
            d = random_date(date(2024, 1, 1), date(2024, 12, 31))
            tgl = d.strftime('%d-%m-%Y')
        else:
            d = random_date(WAKTU_START, WAKTU_END)
            tgl = d.strftime('%d-%m-%Y')  # format dd-mm-yyyy (dayfirst=True)

        # Nasabah: ~5% kosong, ~3% kode tidak terdaftar -> fallback id=0 (UNKNOWN)
        roll_nas = random.random()
        if roll_nas < 0.05:
            nasabah_code = ''
        elif roll_nas < 0.08:
            nasabah_code = 'N-99999'
        else:
            nasabah_code = random.choice(nasabah_codes)

        # Merchant: banyak transaksi non-merchant (mis. transfer/ATM) -> ~40% kosong
        if random.random() < 0.40:
            merchant_code = ''
        else:
            merchant_code = random.choice(merchant_codes)

        channel = random.choice(CHANNEL_VALUES)
        kota = random.choice(KOTA_VALUES)

        # Nominal: ~3% negatif (data tidak valid -> di-drop), sisanya wajar
        nominal_int = random.randint(10_000, 10_000_000)
        if random.random() < 0.03:
            nominal_int = -nominal_int
        nominal = fmt_nominal(nominal_int)

        # Biaya admin: ~5% kosong -> NaN -> di-fillna(0)
        biaya_admin = '' if random.random() < 0.05 else round(random.choice([0, 2500, 6500]), 1)

        rows.append({
            'trx_id': trx_id,
            'tgl_transaksi': tgl,
            'nasabah_code': nasabah_code,
            'channel': channel,
            'merchant_code': merchant_code,
            'kota': kota,
            'nominal': nominal,
            'biaya_admin': biaya_admin,
        })

    df = pd.DataFrame(rows)

    # ~2% trx_id duplikat -> ditangani drop_duplicates(subset=['trx_id']) di etl_fakta.py
    n_dupes = max(1, int(N_TRANSAKSI * 0.02))
    dupe_rows = df.sample(n=n_dupes, random_state=SEED).copy()
    df = pd.concat([df, dupe_rows], ignore_index=True)
    df = df.sample(frac=1, random_state=SEED).reset_index(drop=True)  # acak urutan baris

    return df


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    df_waktu = gen_dim_waktu()
    df_nasabah = gen_nasabah()
    df_merchant = gen_merchant()
    df_trx = gen_transaksi(df_nasabah['nasabah_code'].tolist(), df_merchant['merchant_code'].tolist())

    df_waktu.to_csv(os.path.join(OUTPUT_DIR, 'dim_waktu_clean.csv'), sep=';', index=False)
    df_nasabah.to_csv(os.path.join(OUTPUT_DIR, 'nasabah_crm.csv'), sep=';', index=False)
    df_merchant.to_csv(os.path.join(OUTPUT_DIR, 'merchant_mms.csv'), sep=';', index=False)
    df_trx.to_csv(os.path.join(OUTPUT_DIR, 'transaksi_raw.csv'), sep=';', index=False)

    print(">>> Data generate selesai!")
    print(f"    dim_waktu_clean.csv : {len(df_waktu)} baris")
    print(f"    nasabah_crm.csv     : {len(df_nasabah)} baris")
    print(f"    merchant_mms.csv    : {len(df_merchant)} baris")
    print(f"    transaksi_raw.csv   : {len(df_trx)} baris (termasuk duplikat trx_id)")
    print(f"    -> Disimpan di: {OUTPUT_DIR}")


if __name__ == '__main__':
    main()