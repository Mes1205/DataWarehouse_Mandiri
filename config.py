# config.py
# Konfigurasi koneksi database PostgreSQL (dihost di Aiven Cloud).
# Semua modul ETL mengimpor get_engine() dari sini agar koneksi terpusat
# dan mudah diganti (misal: ganti dari Aiven ke local) tanpa ubah file lain.

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

# Ambil DB_URL dari file .env (format: DB_URL=postgresql+psycopg2://user:password@host:port/dbname?sslmode=require)
load_dotenv()
DB_URL = os.environ["DB_URL"]

# Folder sumber CSV untuk ETL — default ke root project (data asli).
# Untuk pakai dataset dummy hasil generate_dirty_data.py, set di .env:
#   DATA_DIR=data/generate1
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, os.environ.get("DATA_DIR", "."))

def get_engine():
    # Membuat SQLAlchemy engine — objek ini yang dipakai pandas (.to_sql, read_sql)
    # dan sqlalchemy (text queries) untuk berkomunikasi dengan PostgreSQL.
    return create_engine(DB_URL)
