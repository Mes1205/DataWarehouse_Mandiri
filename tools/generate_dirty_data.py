# tools/generate_dirty_data.py
# Generator data dummy "kotor" untuk uji coba pipeline ETL Data Warehouse Mandiri.
#
# Mode ini membuat data LANJUTAN dari data/default_data (1000 nasabah,
# 100 merchant, 5000 transaksi), dipecah jadi beberapa BATCH CSV. Setiap
# batch cocok dipakai sebagai DATA_DIR untuk satu kali run
# `python main.py incremental` (lihat etl/dimensi.py & etl/fakta.py).
#
# dim_waktu_clean.csv (kalender 2001-2030) SUDAH ada di data/default_data --
# generator ini TIDAK generate file itu lagi.
#
# Per batch:
#   - merchant_mms.csv    : N_MERCHANT merchant baru (lanjutan kode dari batch sebelumnya)
#   - nasabah_crm.csv     : N_NASABAH nasabah baru (lanjutan kode dari batch sebelumnya)
#   - transaksi_raw.csv   : N_TRANSAKSI transaksi baru. nasabah_code, merchant_code,
#     channel, dan kota mayoritas diambil dari kode yang sudah terdaftar (default_data +
#     batch-batch sebelumnya). Hanya ~UNKNOWN_RATE (default 2%) baris yang sengaja
#     punya salah satu dari 4 field itu kosong -> jatuh ke baris "Unknown" (id=0)
#     di dimensi terkait, supaya rasio Unknown di fact_transaksi terkendali kecil
#     dan tidak makin besar seiring data bertambah.
#
#     PENTING — tanggal transaksi tiap batch dibuat MAJU & TIDAK OVERLAP (lihat
#     TRX_START/TRX_END & split_date_range()) supaya watermark incremental
#     (MAX(waktu_id) di fact_transaksi, lihat etl/fakta.py run_fakta_incremental)
#     selalu naik per batch dan transaksinya benar-benar ke-insert. TRX_START
#     adalah hari setelah tanggal transaksi terakhir di data/default_data
#     (2026-04-11), TRX_END = akhir kalender dim_waktu (2030-12-31).
#
# Variasi "kotor" yang TETAP dipertahankan (semua sudah ditangani ETL, BUKAN Unknown):
#   - channel: variasi penulisan (BIFAST/bifast/qris/livin dst) -> dinormalisasi
#     oleh map_channel di etl/fakta.py, hasilnya tetap channel yang valid.
#   - kota: variasi singkatan (BDG/Jkt Sel/SBY) -> dinormalisasi oleh MAP_KOTA
#     di etl/wilayah_data.py, hasilnya tetap kota yang valid.
#   - jenis_kelamin / segmen_nasabah / kategori merchant: variasi penulisan & sebagian kosong
#   - tanggal lahir & tanggal transaksi: sebagian kosong/format tidak valid -> di-drop/NaT
#   - nominal: format ribuan ala Indonesia, sebagian negatif -> di-drop
#   - trx_id: sebagian duplikat -> di-drop_duplicates
#
# Output: data/generate1/batch_NN/*.csv (sep=';', sama seperti CSV sumber asli)

import argparse
import os
import random
import sys
from datetime import date, timedelta

import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from etl.wilayah_data import ALL_KOTA, MAP_KOTA

OUTPUT_ROOT = os.path.join(PROJECT_ROOT, 'data', 'generate1')

# Lanjutan dari data/default_data:
#   nasabah_crm.csv  -> N-10001 .. N-11000  (1000 baris)
#   merchant_mms.csv -> MCH-5001 .. MCH-5100 (100 baris)
#   transaksi_raw.csv-> TRX-200001 .. TRX-204999 (5000 baris)
START_NASABAH = 11001
START_MERCHANT = 5101
START_TRX = 205000

# Rentang tanggal transaksi untuk seluruh batch (dibagi rata & berurutan per
# batch, lihat split_date_range()). TRX_START = sehari setelah tanggal transaksi
# terakhir di data/default_data (2026-04-11); TRX_END = akhir dim_waktu_clean (2030-12-31).
TRX_START = date(2026, 4, 12)
TRX_END = date(2030, 12, 31)

DEFAULT_BATCHES = 20
DEFAULT_N_MERCHANT = 100
DEFAULT_N_NASABAH = 1000
DEFAULT_N_TRANSAKSI = 10000

# Persentase transaksi yang sengaja punya 1 field (nasabah_code/merchant_code/
# channel/kota) dikosongkan -> jatuh ke baris "Unknown" (id=0) di dimensi terkait.
UNKNOWN_RATE = 0.02

FIRST_NAMES = ['Andi', 'Budi', 'Citra', 'Dewi', 'Eka', 'Fajar', 'Gita', 'Hadi',
               'Indah', 'Joko', 'Kartika', 'Lutfi', 'Maya', 'Nanda', 'Oki',
               'Putri', 'Rizal', 'Sari', 'Tono', 'Umi', 'Vina', 'Wawan', 'Yuni', 'Zaki']
LAST_NAMES = ['Saputra', 'Wijaya', 'Lestari', 'Pratama', 'Santoso', 'Hidayat',
              'Maharani', 'Kusuma', 'Permata', 'Hakim', 'Utami', 'Setiawan']

MERCHANT_PREFIX = ['Toko', 'Warung', 'Resto', 'Cafe', 'Apotek', 'Bengkel', 'Minimarket', 'Klinik']
MERCHANT_SUFFIX = ['Mandiri', 'Sejahtera', 'Jaya', 'Makmur', 'Berkah', 'Sentosa', 'Abadi', 'Indah']

# Variasi "kotor" — semua sudah ditangani oleh map_jk / fillna di etl/dimensi.py
JK_VALUES = ['L', 'P', 'M', 'Laki-laki', 'Female', 'Pria', 'Wanita', '']

# Sudah ditangani fillna('Reguler') + replace({'RETAIL':'Reguler','prio':'Prioritas'})
SEGMEN_VALUES = ['Reguler', 'Prioritas', 'RETAIL', 'prio', 'Private', '']

# Sudah ditangani fillna('Unknown') di dim_merchant
KATEGORI_VALUES = ['Retail', 'F&B', 'Food & Beverage', 'Health', 'Kesehatan',
                    'Market', 'Electronics', '']

# Channel yang lolos map_channel di etl/fakta.py -- variasi penulisan
# (BIFAST/bifast/qris/livin dst) dinormalisasi jadi channel valid, BUKAN UNKNOWN.
CHANNEL_VALUES = ['ATM', 'BI_FAST', 'BIFAST', 'bifast', 'QRIS', 'qris', 'ATM_LINK', 'LIVIN', 'livin']

# Kota dari master list wilayah Indonesia (etl/wilayah_data.ALL_KOTA), ditambah
# variasi singkatan (MAP_KOTA) yang dinormalisasi jadi kota valid, BUKAN UNKNOWN.
KOTA_VALUES = ALL_KOTA + list(MAP_KOTA.keys())


def random_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def split_date_range(start: date, end: date, n: int):
    """Bagi [start, end] jadi n rentang berurutan & tidak overlap (sisa hari
    dibagikan ke batch-batch pertama). Dipakai supaya tanggal transaksi tiap
    batch maju, sehingga watermark incremental (MAX waktu_id) selalu naik."""
    total_days = (end - start).days + 1
    chunk, remainder = divmod(total_days, n)

    ranges = []
    cur = start
    for i in range(n):
        days = chunk + (1 if i < remainder else 0)
        chunk_end = cur + timedelta(days=days - 1)
        ranges.append((cur, chunk_end))
        cur = chunk_end + timedelta(days=1)
    return ranges


def gen_nasabah(start_id, n):
    rows = []
    for i in range(n):
        code_num = start_id + i
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
            'nasabah_code': f"N-{code_num}",
            'nama_lengkap': nama,
            'jenis_kelamin': jk,
            'tanggal_lahir': ttl,
            'segmen_nasabah': segmen,
        })
    return pd.DataFrame(rows)


def gen_merchant(start_id, n):
    rows = []
    for i in range(n):
        code_num = start_id + i
        nama = f"{random.choice(MERCHANT_PREFIX)} {random.choice(MERCHANT_SUFFIX)} {code_num}"
        kategori = random.choice(KATEGORI_VALUES)
        rows.append({
            'merchant_code': f"MCH-{code_num}",
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


def gen_transaksi(start_trx_id, n, nasabah_pool, merchant_pool, seed, tgl_start, tgl_end):
    rows = []

    for i in range(n):
        trx_id = f"TRX-{start_trx_id + i}"

        # Tanggal transaksi: ~2% kosong, ~2% format tidak valid -> di-drop oleh ETL.
        # Tanggal valid diambil dari [tgl_start, tgl_end] -- rentang khusus batch
        # ini (lihat split_date_range di main()) supaya watermark incremental naik.
        roll_date = random.random()
        if roll_date < 0.02:
            tgl = ''  # kosong -> baris di-drop oleh ETL (waktu_id NaN)
        elif roll_date < 0.04:
            tgl = '31-13-2026'  # bulan tidak valid -> NaT -> di-drop
        else:
            d = random_date(tgl_start, tgl_end)
            tgl = d.strftime('%d-%m-%Y')  # format dd-mm-yyyy (dayfirst=True)

        # nasabah_code, merchant_code, channel, kota: normalnya SELALU dari kode/
        # nilai yang sudah terdaftar & valid. Hanya ~UNKNOWN_RATE baris yang sengaja
        # punya SATU dari 4 field ini dikosongkan -> dibaca sbg NaN -> jatuh ke
        # baris "Unknown" (id=0) di dim_nasabah/dim_merchant/dim_channel/dim_wilayah.
        nasabah_code = random.choice(nasabah_pool)
        merchant_code = random.choice(merchant_pool)
        channel = random.choice(CHANNEL_VALUES)
        kota = random.choice(KOTA_VALUES)

        if random.random() < UNKNOWN_RATE:
            field = random.choice(['nasabah_code', 'merchant_code', 'channel', 'kota'])
            if field == 'nasabah_code':
                nasabah_code = ''
            elif field == 'merchant_code':
                merchant_code = ''
            elif field == 'channel':
                channel = ''
            else:
                kota = ''

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

    # ~2% trx_id duplikat -> ditangani drop_duplicates(subset=['trx_id']) di etl/fakta.py
    n_dupes = max(1, int(n * 0.02))
    dupe_rows = df.sample(n=n_dupes, random_state=seed).copy()
    df = pd.concat([df, dupe_rows], ignore_index=True)
    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)  # acak urutan baris

    return df


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--batches', type=int, default=DEFAULT_BATCHES,
                    help=f"Jumlah batch yang digenerate (default: {DEFAULT_BATCHES})")
    p.add_argument('--n-merchant', type=int, default=DEFAULT_N_MERCHANT,
                    help=f"Jumlah merchant baru per batch (default: {DEFAULT_N_MERCHANT})")
    p.add_argument('--n-nasabah', type=int, default=DEFAULT_N_NASABAH,
                    help=f"Jumlah nasabah baru per batch (default: {DEFAULT_N_NASABAH})")
    p.add_argument('--n-transaksi', type=int, default=DEFAULT_N_TRANSAKSI,
                    help=f"Jumlah transaksi baru per batch (default: {DEFAULT_N_TRANSAKSI})")
    p.add_argument('--start-merchant', type=int, default=START_MERCHANT,
                    help=f"Nomor awal kode merchant baru, MCH-<n> (default: {START_MERCHANT})")
    p.add_argument('--start-nasabah', type=int, default=START_NASABAH,
                    help=f"Nomor awal kode nasabah baru, N-<n> (default: {START_NASABAH})")
    p.add_argument('--start-trx', type=int, default=START_TRX,
                    help=f"Nomor awal trx_id baru, TRX-<n> (default: {START_TRX})")
    p.add_argument('--output-dir', default=OUTPUT_ROOT,
                    help=f"Folder output, akan dibuat batch_01..batch_NN di dalamnya (default: {OUTPUT_ROOT})")
    p.add_argument('--seed', type=int, default=42, help="Random seed (default: 42)")
    return p.parse_args()


def main():
    args = parse_args()
    random.seed(args.seed)

    os.makedirs(args.output_dir, exist_ok=True)

    # Rentang tanggal transaksi per batch -- berurutan & tidak overlap supaya
    # watermark incremental (MAX waktu_id) selalu naik dari batch ke batch.
    date_ranges = split_date_range(TRX_START, TRX_END, args.batches)

    # Pool kode nasabah/merchant yang sudah "terdaftar" (default_data + batch
    # sebelumnya), dipakai sebagai sumber valid untuk transaksi tiap batch.
    nasabah_pool = [f"N-{n}" for n in range(10001, args.start_nasabah)]
    merchant_pool = [f"MCH-{m}" for m in range(5001, args.start_merchant)]

    next_nasabah = args.start_nasabah
    next_merchant = args.start_merchant
    next_trx = args.start_trx

    for batch in range(1, args.batches + 1):
        batch_dir = os.path.join(args.output_dir, f"batch_{batch:02d}")
        os.makedirs(batch_dir, exist_ok=True)

        df_nasabah = gen_nasabah(next_nasabah, args.n_nasabah)
        df_merchant = gen_merchant(next_merchant, args.n_merchant)

        nasabah_pool = nasabah_pool + df_nasabah['nasabah_code'].tolist()
        merchant_pool = merchant_pool + df_merchant['merchant_code'].tolist()

        tgl_start, tgl_end = date_ranges[batch - 1]
        df_trx = gen_transaksi(
            next_trx, args.n_transaksi, nasabah_pool, merchant_pool,
            seed=args.seed + batch, tgl_start=tgl_start, tgl_end=tgl_end,
        )

        df_nasabah.to_csv(os.path.join(batch_dir, 'nasabah_crm.csv'), sep=';', index=False)
        df_merchant.to_csv(os.path.join(batch_dir, 'merchant_mms.csv'), sep=';', index=False)
        df_trx.to_csv(os.path.join(batch_dir, 'transaksi_raw.csv'), sep=';', index=False)

        print(f">>> Batch {batch:02d} -> {batch_dir}  (tanggal {tgl_start} s/d {tgl_end})")
        print(f"    nasabah_crm.csv     : {len(df_nasabah)} baris (N-{next_nasabah}..N-{next_nasabah + args.n_nasabah - 1})")
        print(f"    merchant_mms.csv    : {len(df_merchant)} baris (MCH-{next_merchant}..MCH-{next_merchant + args.n_merchant - 1})")
        print(f"    transaksi_raw.csv   : {len(df_trx)} baris (termasuk duplikat trx_id, mulai TRX-{next_trx})")

        next_nasabah += args.n_nasabah
        next_merchant += args.n_merchant
        next_trx += args.n_transaksi

    print("\n>>> Selesai generate semua batch!")
    print(f"    Total nasabah baru  : {args.batches * args.n_nasabah}")
    print(f"    Total merchant baru : {args.batches * args.n_merchant}")
    print(f"    Total transaksi baru: {args.batches * args.n_transaksi}")
    print(f"    Output: {args.output_dir}/batch_01 .. batch_{args.batches:02d}")
    print("\n    Cara pakai: set DATA_DIR di .env ke salah satu folder batch lalu")
    print("    jalankan `python main.py incremental` secara berurutan per batch.")


if __name__ == '__main__':
    main()
