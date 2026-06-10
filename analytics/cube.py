# analytics/cube.py
# Membangun OLAP Cube (in-memory, multidimensional) di atas Star Schema
# Data Warehouse Mandiri menggunakan atoti.
#
# Kenapa file ini ada:
#   Paper menyebutkan bahwa menghubungkan BI tool (Looker Studio/Data Studio)
#   langsung ke Star Schema relasional menimbulkan bottleneck karena BI tool
#   harus melakukan multidimensional JOIN berulang-ulang. Solusi di paper
#   adalah PostgreSQL Materialized View (mvw_dashboard_transaksi).
#
#   atoti adalah pendekatan alternatif/komplementer: cube melakukan JOIN
#   antar fact & dimensi serta agregasi (SUM, COUNT, AVG, dst) di memory,
#   sehingga query OLAP (slice, dice, drill-down) tidak perlu menyentuh
#   Postgres lagi setelah data dimuat. Hasilnya bisa dieksplorasi lewat
#   Atoti Web UI (pivot table interaktif) di browser.
#
# Source data:
#   Tabel Star Schema yang sudah diisi oleh main.py / etl/dimensi.py /
#   etl/fakta.py: fact_transaksi, dim_waktu, dim_nasabah, dim_channel,
#   dim_wilayah, dim_merchant. Koneksi pakai config.get_engine() yang sama
#   dengan modul ETL lain (DB_URL dari .env).
#
# Cara pakai:
#   1. (sekali saja) buat venv Python 3.11 — atoti belum mendukung Python
#      versi terbaru — lalu install dependency:
#        python3.11 -m venv .venv && source .venv/bin/activate
#        pip install atoti pandas sqlalchemy psycopg2-binary python-dotenv
#   2. Pastikan .env (DB_URL) sudah terisi (lihat config.py).
#   3. Jalankan: python -m analytics.cube
#   4. Buka URL Atoti Web App yang dicetak di terminal untuk eksplorasi
#      cube secara interaktif (drag-and-drop pivot table).

import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import atoti as tt
from config import get_engine


def _load_star_schema():
    """EXTRACT seluruh tabel Star Schema dari PostgreSQL (Aiven) sebagai DataFrame."""
    engine = get_engine()
    print(">>> Membaca tabel Star Schema dari PostgreSQL...")

    fact        = pd.read_sql("SELECT * FROM fact_transaksi", engine)
    dim_waktu   = pd.read_sql("SELECT * FROM dim_waktu",    engine)
    dim_nasabah = pd.read_sql("SELECT * FROM dim_nasabah",  engine)
    dim_channel = pd.read_sql("SELECT * FROM dim_channel",  engine)
    dim_wilayah = pd.read_sql("SELECT * FROM dim_wilayah",  engine)
    dim_merchant= pd.read_sql("SELECT * FROM dim_merchant", engine)

    # Kolom NUMERIC di Postgres dibaca psycopg2 sebagai Decimal (dtype=object).
    # atoti butuh tipe numerik native (float) untuk measure SUM/AVG.
    fact['nominal_transaksi'] = fact['nominal_transaksi'].astype(float)
    fact['biaya_admin']       = fact['biaya_admin'].astype(float)

    # Kolom DATE dibaca sebagai object (datetime.date) — convert ke datetime64
    # supaya level hierarchy "tanggal" dikenali atoti sebagai tipe tanggal.
    dim_waktu['tanggal']        = pd.to_datetime(dim_waktu['tanggal'])
    dim_nasabah['tanggal_lahir'] = pd.to_datetime(dim_nasabah['tanggal_lahir'], errors='coerce')

    print(f"    fact_transaksi : {len(fact)} baris")
    print(f"    dim_waktu      : {len(dim_waktu)} baris")
    print(f"    dim_nasabah    : {len(dim_nasabah)} baris")
    print(f"    dim_channel    : {len(dim_channel)} baris")
    print(f"    dim_wilayah    : {len(dim_wilayah)} baris")
    print(f"    dim_merchant   : {len(dim_merchant)} baris")

    return fact, dim_waktu, dim_nasabah, dim_channel, dim_wilayah, dim_merchant


def build_cube():
    """Bangun atoti Session + Cube dari Star Schema. Return (session, cube)."""
    fact_df, waktu_df, nasabah_df, channel_df, wilayah_df, merchant_df = _load_star_schema()

    session = tt.Session.start()

    # -------------------------
    # LOAD TABLES KE ATOTI
    # -------------------------
    # keys=[...] menandai surrogate key (PK) tiap tabel — dipakai atoti untuk JOIN.
    #
    # default_values=... wajib diisi untuk setiap kolom yang nanti dipakai
    # sebagai level hierarchy. atoti memperlakukan semua kolom hasil
    # read_pandas sebagai nullable; sebuah hierarchy hanya bisa dibangun di
    # atas kolom non-nullable (yaitu kolom yang punya default value).
    # Nilai default ini sebenarnya tidak pernah terpakai karena tabel sumber
    # di Postgres sudah NOT NULL (lihat DDL) — hanya untuk memenuhi syarat atoti.
    fact = session.read_pandas(
        fact_df, table_name="Fact_Transaksi", keys=["fact_id"]
    )
    # NB: atoti menolak "" (empty string) sebagai default value untuk kolom
    # bertipe String, jadi dipakai placeholder non-kosong "Unknown".
    dim_waktu = session.read_pandas(
        waktu_df, table_name="Dim_Waktu", keys=["waktu_id"],
        default_values={"tahun": 0, "quarter": "Unknown", "bulan": "Unknown", "hari": "Unknown",
                         "tanggal": datetime.date(1900, 1, 1)},
    )
    dim_nasabah = session.read_pandas(
        nasabah_df, table_name="Dim_Nasabah", keys=["nasabah_id"],
        default_values={"segmen_nasabah": "Unknown", "jenis_kelamin": "Unknown", "nama_lengkap": "Unknown"},
    )
    dim_channel = session.read_pandas(
        channel_df, table_name="Dim_Channel", keys=["channel_id"],
        default_values={"jenis_channel": "Unknown", "nama_channel": "Unknown"},
    )
    dim_wilayah = session.read_pandas(
        wilayah_df, table_name="Dim_Wilayah", keys=["wilayah_id"],
        default_values={"region": "Unknown", "provinsi": "Unknown", "kota": "Unknown"},
    )
    dim_merchant = session.read_pandas(
        merchant_df, table_name="Dim_Merchant", keys=["merchant_id"],
        default_values={"kategori": "Unknown", "nama_merchant": "Unknown"},
    )

    # -------------------------
    # JOIN — replikasi relasi Star Schema (FK fact -> PK dimensi)
    # -------------------------
    # Setiap dimensi punya baris "Unknown" id=0 sehingga FK fact selalu
    # punya pasangan (referential integrity terjaga, lihat etl/dimensi.py).
    fact.join(dim_waktu,    fact["waktu_id"]    == dim_waktu["waktu_id"])
    fact.join(dim_nasabah,  fact["nasabah_id"]  == dim_nasabah["nasabah_id"])
    fact.join(dim_channel,  fact["channel_id"]  == dim_channel["channel_id"])
    fact.join(dim_wilayah,  fact["wilayah_id"]  == dim_wilayah["wilayah_id"])
    fact.join(dim_merchant, fact["merchant_id"] == dim_merchant["merchant_id"])

    # mode="manual": tidak auto-generate hierarchy/measure dari semua kolom,
    # supaya struktur cube persis mengikuti desain dimensional di paper.
    cube = session.create_cube(fact, "CUBE_TRANSAKSI_MANDIRI", mode="manual")
    h, l, m = cube.hierarchies, cube.levels, cube.measures

    # -------------------------
    # HIERARCHIES (drill-down per dimensi, urut dari level paling umum -> rinci)
    # -------------------------

    # dim_waktu -> Time-Series Analytics (Section IV.G.6)
    h["Waktu"] = [dim_waktu["tahun"], dim_waktu["quarter"], dim_waktu["bulan"], dim_waktu["tanggal"]]
    h["Hari Transaksi"] = [dim_waktu["hari"]]  # untuk analisis "peak transaction day"

    # Urutan kronologis (bukan alfabetis) — nilai disimpan dalam bahasa Inggris
    # (lihat etl/dimensi.py: dim_waktu_clean.csv sudah berisi nama bulan/hari Inggris)
    h["Waktu"]["bulan"].order = tt.CustomOrder(first_elements=[
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ])
    h["Hari Transaksi"]["hari"].order = tt.CustomOrder(first_elements=[
        "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
    ])

    # dim_nasabah -> Customer Segmentation Analytics (Section IV.G.3)
    h["Nasabah"] = [
        dim_nasabah["segmen_nasabah"],
        dim_nasabah["jenis_kelamin"],
        dim_nasabah["nama_lengkap"],
    ]

    # dim_channel -> Digital Channel Analytics (Section IV.G.2)
    h["Channel"] = [dim_channel["jenis_channel"], dim_channel["nama_channel"]]

    # Hierarchy flat (1 level) khusus nama_channel — dipakai di chart yang
    # butuh label bersih ("BI_FAST") tanpa prefix path "jenis_channel" (mis.
    # pie chart "Analisis Channel" di dashboard Atoti, lihat path member di
    # hierarchy "Channel" yang selalu ikut "Digital, BI_FAST" dst).
    h["Nama Channel"] = [dim_channel["nama_channel"]]

    # dim_wilayah -> Geographic Analytics (Section IV.G.5)
    h["Wilayah"] = [dim_wilayah["region"], dim_wilayah["provinsi"], dim_wilayah["kota"]]

    # dim_merchant -> Merchant Ecosystem Analytics (Section IV.G.4)
    h["Merchant"] = [dim_merchant["kategori"], dim_merchant["nama_merchant"]]

    # -------------------------
    # MEASURES — High-Level KPI Analytics (Section IV.G.1)
    # -------------------------
    m["Total Volume Transaksi"] = tt.agg.sum(fact["nominal_transaksi"])
    m["Total Biaya Admin"]      = tt.agg.sum(fact["biaya_admin"])

    # Jumlah baris fakta yang berkontribusi pada sebuah cell
    # -> "Total Frekuensi Transaksi" di paper.
    m["Jumlah Transaksi"] = tt.agg.count_distinct(fact["fact_id"])

    # Average transaction value
    m["Rata-rata Nominal Transaksi"] = (
        m["Total Volume Transaksi"] / m["Jumlah Transaksi"]
    )

    for measure_name in ("Total Volume Transaksi", "Total Biaya Admin", "Rata-rata Nominal Transaksi"):
        m[measure_name].formatter = "DOUBLE[#,##0.00]"

    return session, cube


def run_sample_queries(cube):
    """Jalankan beberapa query OLAP yang merepresentasikan dashboard di paper
    (Section IV.D, sub-bagian 1-7) untuk memverifikasi cube sudah benar."""
    l, m = cube.levels, cube.measures

    print("\n=== 1. High-Level KPI ===")
    print(cube.query(
        m["Total Volume Transaksi"], m["Jumlah Transaksi"],
        m["Total Biaya Admin"], m["Rata-rata Nominal Transaksi"],
    ))

    print("\n=== 2. Digital Channel Analytics ===")
    print(cube.query(m["Total Volume Transaksi"], m["Jumlah Transaksi"], levels=[l["Channel", "nama_channel"]]))

    print("\n=== 3. Customer Segmentation (Segmen Nasabah x Gender) ===")
    print(cube.query(m["Total Volume Transaksi"], levels=[l["segmen_nasabah"], l["jenis_kelamin"]]))

    print("\n=== 4. Merchant Ecosystem (Top Kategori Merchant) ===")
    print(cube.query(m["Total Volume Transaksi"], levels=[l["kategori"]]))

    print("\n=== 5. Geographic Analytics (Top Kota) ===")
    print(cube.query(m["Total Volume Transaksi"], levels=[l["kota"]]))

    print("\n=== 6. Time-Series — Tren Bulanan ===")
    print(cube.query(m["Total Volume Transaksi"], levels=[l["bulan"]]))

    print("\n=== 6b. Peak Transaction Day ===")
    print(cube.query(m["Jumlah Transaksi"], levels=[l["hari"]]))

    print("\n=== 7. Regional Channel Utilization (Kota x Channel) ===")
    print(cube.query(m["Jumlah Transaksi"], levels=[l["kota"], l["Channel", "nama_channel"]]))


if __name__ == "__main__":
    print("=" * 40)
    print("   BUILD OLAP CUBE - DW MANDIRI (atoti)")
    print("=" * 40)

    session, cube = build_cube()

    print(f"\n>>> Atoti Web App siap diakses di: {session.url}")
    print("    (buka URL di atas untuk eksplorasi cube interaktif)")

    run_sample_queries(cube)

    print("\n>>> Session tetap berjalan. Tekan Ctrl+C untuk berhenti.")
    session.wait()
