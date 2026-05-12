# export_to_csv.py
import pandas as pd
import os
from config import get_engine

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'output_csv')

def export_semua():
    print(">>> Mulai Export CSV...")
    engine = get_engine()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    tabel = [
        'dim_waktu',
        'dim_nasabah',
        'dim_merchant',
        'dim_channel',
        'dim_wilayah',
        'fact_transaksi',
    ]

    for nama in tabel:
        print(f"    -> Export {nama}...")
        df = pd.read_sql(f"SELECT * FROM {nama} ORDER BY 1", engine)
        path = os.path.join(OUTPUT_DIR, f"{nama}.csv")
        df.to_csv(path, index=False, sep=';')
        print(f"       {len(df)} baris → {path}")

    print(">>> Export SELESAI!")
    print(f"    Cek folder: {OUTPUT_DIR}")

if __name__ == '__main__':
    export_semua()