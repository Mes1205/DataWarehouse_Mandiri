# main.py
from etl_dimensi import run_dimensi
from etl_fakta import run_fakta
from config import get_engine
from sqlalchemy import text
from etl_fakta import create_materialized_view

def truncate_semua_tabel(engine):
    """Kosongkan semua tabel sebelum insert ulang — urutan penting karena FK"""
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE fact_transaksi RESTART IDENTITY CASCADE"))
        conn.execute(text("TRUNCATE TABLE dim_waktu     RESTART IDENTITY CASCADE"))
        conn.execute(text("TRUNCATE TABLE dim_nasabah   RESTART IDENTITY CASCADE"))
        conn.execute(text("TRUNCATE TABLE dim_merchant  RESTART IDENTITY CASCADE"))
        conn.execute(text("TRUNCATE TABLE dim_channel   RESTART IDENTITY CASCADE"))
        conn.execute(text("TRUNCATE TABLE dim_wilayah   RESTART IDENTITY CASCADE"))
    print("    -> Semua tabel berhasil dikosongkan")



if __name__ == "__main__":
    print("=" * 40)
    print("   START PIPELINE ETL MANDIRI")
    print("=" * 40)
    try:
        engine = get_engine()

        print(">>> Truncate tabel lama...")
        truncate_semua_tabel(engine)
        print("-" * 40)

        run_dimensi()
        run_fakta()
        # Eksekusi setelah tabel fakta terisi
        create_materialized_view() 
        print("DONE. Cek Looker Studio lu.")

        

    except Exception as e:
        import traceback
        print(f"\nERROR: {e}")
        traceback.print_exc()
