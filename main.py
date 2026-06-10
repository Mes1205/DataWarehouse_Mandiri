# main.py
# Entry point pipeline ETL Data Warehouse Mandiri.
#
# Mode FULL (default):
#   1. Truncate semua tabel (bersihkan data lama)
#   2. run_dimensi() → isi 5 tabel dimensi dari CSV
#   3. run_fakta()   → isi tabel fakta, join ke dimensi untuk dapat surrogate key
#   4. create_materialized_view() → buat view denormalisasi untuk Looker Studio
#
# Mode INCREMENTAL (python3 main.py incremental):
#   1. (tidak ada truncate)
#   2. run_dimensi_incremental() → insert hanya baris dimensi dengan natural key baru
#   3. run_fakta_incremental()   → insert hanya transaksi dengan waktu_id > watermark
#   4. create_materialized_view() → refresh view
#
# Urutan ini wajib dipertahankan: fakta butuh dimensi sudah ada (FK constraint),
# dan materialized view butuh tabel fakta sudah terisi.

import sys
from etl_dimensi import run_dimensi, run_dimensi_incremental
from etl_fakta import run_fakta, run_fakta_incremental
from config import get_engine
from sqlalchemy import text
from etl_fakta import create_materialized_view

def truncate_semua_tabel(engine):
    """Kosongkan semua tabel sebelum insert ulang — urutan penting karena FK"""
    # fact_transaksi di-truncate duluan karena dia punya FK ke semua dimensi.
    # CASCADE memastikan sequence (SERIAL/IDENTITY) juga di-reset ke 1.
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE fact_transaksi RESTART IDENTITY CASCADE"))
        conn.execute(text("TRUNCATE TABLE dim_waktu     RESTART IDENTITY CASCADE"))
        conn.execute(text("TRUNCATE TABLE dim_nasabah   RESTART IDENTITY CASCADE"))
        conn.execute(text("TRUNCATE TABLE dim_merchant  RESTART IDENTITY CASCADE"))
        conn.execute(text("TRUNCATE TABLE dim_channel   RESTART IDENTITY CASCADE"))
        conn.execute(text("TRUNCATE TABLE dim_wilayah   RESTART IDENTITY CASCADE"))
    print("    -> Semua tabel berhasil dikosongkan")



if __name__ == "__main__":
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "full"
    if mode not in ("full", "incremental"):
        print(f"Mode '{mode}' tidak dikenal. Gunakan 'full' atau 'incremental'.")
        sys.exit(1)

    print("=" * 40)
    print(f"   START PIPELINE ETL MANDIRI ({mode.upper()})")
    print("=" * 40)
    try:
        engine = get_engine()

        if mode == "full":
            print(">>> Truncate tabel lama...")
            truncate_semua_tabel(engine)
            print("-" * 40)

            # Step 2: isi semua dimensi (waktu, nasabah, merchant, channel, wilayah)
            run_dimensi()

            # Step 3: isi fact_transaksi dengan surrogate key dari dimensi
            run_fakta()
        else:
            # Incremental: tanpa truncate, hanya insert data baru
            run_dimensi_incremental()
            run_fakta_incremental()

        # Step 4: buat materialized view denormalisasi untuk dashboard Looker Studio
        create_materialized_view()
        print("DONE. Cek Looker Studio lu.")



    except Exception as e:
        import traceback
        print(f"\nERROR: {e}")
        traceback.print_exc()
