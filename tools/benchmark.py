# tools/benchmark.py
# Benchmark end-to-end scalability DW Mandiri.
# Tidak mengubah implementasi apapun — hanya mengukur fungsi yang sudah ada.
#
# Subcommands:
#   etl     — ukur waktu pipeline ETL (full load atau incremental per batch)
#   cube    — ukur cube build time + memory usage
#   query   — ukur response time 7 OLAP query × 30 repetisi
#   quality — ukur ETL data quality metrics dari CSV sumber + DB
#
# Usage:
#   # Scale-S: truncate DB dulu, lalu:
#   python tools/benchmark.py etl   --scale S --mode full
#   python tools/benchmark.py cube  --scale S
#   python tools/benchmark.py query --scale S
#
#   # Scale-M: setelah run incremental batch_01..05:
#   python tools/benchmark.py etl   --scale M --mode incremental
#   python tools/benchmark.py cube  --scale M
#   python tools/benchmark.py query --scale M
#
#   # ETL Quality (jalankan saat DATA_DIR=data/default_data):
#   python tools/benchmark.py quality
#
#   # Analisis & chart (setelah semua skala selesai):
#   python tools/analyze.py

import argparse
import csv
import os
import statistics
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ.setdefault("ATOTI_HIDE_EULA_MESSAGE", "True")

# Paksa semua get_engine() di ETL pakai NullPool supaya koneksi langsung
# ditutup setelah dipakai — mencegah connection slot Aiven habis saat
# benchmark jalan banyak batch berurutan.
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
import config as _config

def _nullpool_engine():
    return create_engine(_config.DB_URL, poolclass=NullPool)

_config.get_engine = _nullpool_engine

RESULTS_DIR = os.path.join(ROOT, "results")

# ── psutil opsional (untuk memory measurement) ─────────────────────────────
try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False
    print("[WARN] psutil tidak terinstall — memory measurement dinonaktifkan.")
    print("       Install dengan: pip install psutil")


# ── Helpers ─────────────────────────────────────────────────────────────────

def _ensure_results():
    os.makedirs(RESULTS_DIR, exist_ok=True)


def _append_csv(filename: str, row: dict):
    path = os.path.join(RESULTS_DIR, filename)
    file_exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def _get_fact_count(engine) -> int:
    from sqlalchemy import text
    with engine.connect() as conn:
        return conn.execute(text("SELECT COUNT(*) FROM fact_transaksi")).scalar()


def _memory_mb() -> float:
    if not _PSUTIL:
        return 0.0
    return psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024


# ── Layer 1: ETL ─────────────────────────────────────────────────────────────

def run_etl(scale: str, mode: str):
    """
    Ukur waktu eksekusi pipeline ETL.
    - mode=full       : truncate → dimensi → fakta → materialized view
    - mode=incremental: dimensi_incremental → fakta_incremental → materialized view
                        (jalankan SETELAH set DATA_DIR ke batch yang diinginkan)
    """
    from config import get_engine
    from etl.dimensi import run_dimensi, run_dimensi_incremental
    from etl.fakta import run_fakta, run_fakta_incremental, create_materialized_view

    engine = get_engine()

    if mode == "full":
        # Truncate sebelum full load
        from sqlalchemy import text
        print("[ETL] Truncating semua tabel untuk full load...")
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE fact_transaksi RESTART IDENTITY CASCADE"))
            conn.execute(text("TRUNCATE TABLE dim_waktu     RESTART IDENTITY CASCADE"))
            conn.execute(text("TRUNCATE TABLE dim_nasabah   RESTART IDENTITY CASCADE"))
            conn.execute(text("TRUNCATE TABLE dim_merchant  RESTART IDENTITY CASCADE"))
            conn.execute(text("TRUNCATE TABLE dim_channel   RESTART IDENTITY CASCADE"))
            conn.execute(text("TRUNCATE TABLE dim_wilayah   RESTART IDENTITY CASCADE"))

    rows_before = _get_fact_count(engine)

    print(f"[ETL] Mulai {mode} load (scale={scale})...")
    t_start = time.perf_counter()

    if mode == "full":
        run_dimensi()
        run_fakta()
    else:
        run_dimensi_incremental()
        run_fakta_incremental()

    create_materialized_view()
    elapsed = time.perf_counter() - t_start

    rows_after    = _get_fact_count(engine)
    rows_loaded   = rows_after - rows_before if mode == "incremental" else rows_after
    throughput    = rows_loaded / elapsed if elapsed > 0 else 0

    row = {
        "scale":            scale,
        "mode":             mode,
        "rows_total_in_db": rows_after,
        "rows_loaded":      rows_loaded,
        "etl_time_sec":     round(elapsed, 3),
        "throughput_rps":   round(throughput, 1),
    }
    _append_csv("etl_benchmark.csv", row)

    print(f"[ETL] DONE | time={elapsed:.2f}s | rows_loaded={rows_loaded:,} | throughput={throughput:,.0f} rows/s")
    return row


# ── Layer 2: Cube Build ──────────────────────────────────────────────────────

def run_cube(scale: str, n_runs: int = 3):
    """
    Ukur cube build time + memory (n_runs kali, lapor median).
    DB harus sudah di-set ke state yang sesuai dengan scale.
    """
    from config import get_engine
    from analytics.cube import build_cube

    engine   = get_engine()
    n_rows   = _get_fact_count(engine)

    build_times  = []
    memory_after = []

    print(f"[CUBE] Mulai cube benchmark (scale={scale}, n_rows={n_rows:,}, runs={n_runs})...")

    for i in range(n_runs):
        mem_before = _memory_mb()
        t_start    = time.perf_counter()

        session, cube = build_cube()
        elapsed = time.perf_counter() - t_start

        mem_now  = _memory_mb()
        mem_used = mem_now - mem_before

        build_times.append(elapsed)
        memory_after.append(mem_now)

        session.close()
        print(f"  Run {i+1}/{n_runs}: build={elapsed:.2f}s | memory_rss={mem_now:.0f}MB | delta_mem={mem_used:.0f}MB")

    row = {
        "scale":              scale,
        "n_rows":             n_rows,
        "median_build_sec":   round(statistics.median(build_times), 3),
        "min_build_sec":      round(min(build_times), 3),
        "max_build_sec":      round(max(build_times), 3),
        "median_memory_mb":   round(statistics.median(memory_after), 1) if _PSUTIL else "N/A",
    }
    _append_csv("cube_benchmark.csv", row)

    print(f"[CUBE] DONE | median_build={row['median_build_sec']}s | memory={row['median_memory_mb']}MB")
    return row


# ── Layer 3: OLAP Query ──────────────────────────────────────────────────────

# 7 query yang diuji, dikelompokkan per complexity class
QUERY_REGISTRY = {
    # Simple Aggregation: tidak ada level, atau GROUP BY satu dimensi waktu
    "Q1_KPI":          "simple",
    "Q2_MonthlyTrend": "simple",
    # Roll-up: GROUP BY satu dimensi non-waktu
    "Q3_Channel":      "rollup",
    "Q4_Segment":      "rollup",
    "Q5_City":         "rollup",
    # Pivot: GROUP BY dua dimensi sekaligus (cross-dimensional)
    "Q6_ChannelCity":  "pivot",
    "Q7_Heatmap":      "pivot",
}


def _execute_query(name: str, cube):
    """Jalankan satu query OLAP terhadap cube yang sudah dibangun."""
    l = cube.levels
    m = cube.measures

    if name == "Q1_KPI":
        return cube.query(
            m["Total Volume Transaksi"], m["Jumlah Transaksi"], m["Total Biaya Admin"],
            m["Rata-rata Nominal Transaksi"],
        )
    elif name == "Q2_MonthlyTrend":
        return cube.query(
            m["Total Volume Transaksi"], m["Jumlah Transaksi"],
            levels=[l["Waktu", "tahun"], l["Waktu", "bulan"]],
        )
    elif name == "Q3_Channel":
        return cube.query(
            m["Total Volume Transaksi"], m["Jumlah Transaksi"],
            levels=[l["Nama Channel", "nama_channel"]],
        )
    elif name == "Q4_Segment":
        return cube.query(
            m["Total Volume Transaksi"], m["Jumlah Transaksi"],
            levels=[l["Nasabah", "segmen_nasabah"]],
        )
    elif name == "Q5_City":
        return cube.query(
            m["Total Volume Transaksi"], m["Jumlah Transaksi"],
            levels=[l["Wilayah", "kota"]],
        )
    elif name == "Q6_ChannelCity":
        return cube.query(
            m["Jumlah Transaksi"],
            levels=[l["Wilayah", "kota"], l["Nama Channel", "nama_channel"]],
            mode="raw",
        )
    elif name == "Q7_Heatmap":
        return cube.query(
            m["Jumlah Transaksi"],
            levels=[l["Waktu", "bulan"], l["Hari Transaksi", "hari"]],
            mode="raw",
        )


def run_query(scale: str, n_warmup: int = 5, n_runs: int = 30):
    """
    Ukur response time 7 OLAP query × n_runs repetisi (setelah n_warmup warm-up).
    DB harus sudah di-set ke state yang sesuai dengan scale.
    """
    from config import get_engine
    from analytics.cube import build_cube

    engine = get_engine()
    n_rows = _get_fact_count(engine)

    print(f"[QUERY] Building cube (scale={scale}, n_rows={n_rows:,})...")
    session, cube = build_cube()

    # Warm-up: jalankan semua query sekali untuk inisialisasi JVM + cache
    print(f"[QUERY] Warm-up {n_warmup}x per query...")
    for name in QUERY_REGISTRY:
        for _ in range(n_warmup):
            _execute_query(name, cube)

    print(f"[QUERY] Benchmark {n_runs}x per query...")
    for name, complexity in QUERY_REGISTRY.items():
        times_ms = []
        for _ in range(n_runs):
            t0 = time.perf_counter()
            _execute_query(name, cube)
            times_ms.append((time.perf_counter() - t0) * 1000)

        times_sorted = sorted(times_ms)
        p25 = times_sorted[n_runs // 4]
        p75 = times_sorted[(3 * n_runs) // 4]

        row = {
            "scale":      scale,
            "n_rows":     n_rows,
            "query":      name,
            "complexity": complexity,
            "median_ms":  round(statistics.median(times_ms), 3),
            "p25_ms":     round(p25, 3),
            "p75_ms":     round(p75, 3),
            "min_ms":     round(min(times_ms), 3),
            "max_ms":     round(max(times_ms), 3),
        }
        _append_csv("query_benchmark.csv", row)
        print(
            f"  {name:<18} [{complexity}]  "
            f"median={row['median_ms']:7.2f}ms  "
            f"IQR=[{row['p25_ms']:.2f}, {row['p75_ms']:.2f}]"
        )

    session.close()
    print(f"[QUERY] DONE scale={scale}")


# ── ETL Quality ──────────────────────────────────────────────────────────────

def run_quality():
    """
    Hitung ETL data quality metrics dari CSV sumber (DATA_DIR) + DB saat ini.
    Jalankan saat DATA_DIR=data/default_data untuk hasil yang representatif.
    """
    from config import get_engine
    from etl.common import _read_source_csv
    import pandas as pd
    from sqlalchemy import text

    print("[QUALITY] Membaca transaksi_raw.csv dari DATA_DIR...")
    df = _read_source_csv("transaksi_raw.csv")
    if df is None:
        print("[QUALITY] ERROR: transaksi_raw.csv tidak ditemukan di DATA_DIR.")
        print("  Pastikan DATA_DIR=data/default_data di .env lalu coba lagi.")
        return

    total_input = len(df)

    # 1. Duplikat trx_id
    df_dedup    = df.drop_duplicates(subset=["trx_id"])
    n_duplicate = total_input - len(df_dedup)

    # 2. Nominal negatif
    df_check = df_dedup.copy()
    df_check["_nom"] = (
        df_check["nominal"].astype(str).str.strip()
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    df_check["_nom"] = pd.to_numeric(df_check["_nom"], errors="coerce").fillna(0)
    n_negative = int((df_check["_nom"] < 0).sum())

    # 3. Tanggal tidak valid
    df_check["_tgl"] = pd.to_datetime(
        df_check["tgl_transaksi"], dayfirst=True, errors="coerce"
    )
    n_invalid_date = int(df_check["_tgl"].isna().sum())

    total_removed  = n_duplicate + n_negative + n_invalid_date
    quality_rate   = round((total_input - total_removed) / total_input * 100, 2)

    # 4. Unknown mapping dari DB (baris di fact yang FK-nya jatuh ke id=0)
    engine = get_engine()
    with engine.connect() as conn:
        def _count(col):
            return conn.execute(
                text(f"SELECT COUNT(*) FROM fact_transaksi WHERE {col} = 0")
            ).scalar()
        n_unk_nasabah  = _count("nasabah_id")
        n_unk_merchant = _count("merchant_id")
        n_unk_channel  = _count("channel_id")
        n_unk_wilayah  = _count("wilayah_id")
        n_fact_total   = conn.execute(
            text("SELECT COUNT(*) FROM fact_transaksi")
        ).scalar()

    row = {
        "total_input_rows":        total_input,
        "duplicate_removed":       n_duplicate,
        "negative_nominal_removed": n_negative,
        "invalid_date_removed":    n_invalid_date,
        "total_records_removed":   total_removed,
        "data_quality_rate_pct":   quality_rate,
        "unknown_nasabah":         n_unk_nasabah,
        "unknown_merchant":        n_unk_merchant,
        "unknown_channel":         n_unk_channel,
        "unknown_wilayah":         n_unk_wilayah,
        "fact_rows_in_db":         n_fact_total,
    }

    path = os.path.join(RESULTS_DIR, "etl_quality.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        writer.writeheader()
        writer.writerow(row)

    print("\n[QUALITY] Hasil:")
    print(f"  Total input rows        : {total_input:,}")
    print(f"  Duplicate removed       : {n_duplicate:,}")
    print(f"  Negative nominal removed: {n_negative:,}")
    print(f"  Invalid date removed    : {n_invalid_date:,}")
    print(f"  Total removed           : {total_removed:,}")
    print(f"  Data Quality Rate       : {quality_rate}%")
    print(f"  Unknown nasabah mapping : {n_unk_nasabah:,}")
    print(f"  Unknown merchant mapping: {n_unk_merchant:,}")
    print(f"  Unknown channel mapping : {n_unk_channel:,}")
    print(f"  Unknown wilayah mapping : {n_unk_wilayah:,}")
    print(f"  Fact rows in DB         : {n_fact_total:,}")
    print(f"\n  Saved to: {path}")


# ── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Benchmark end-to-end scalability DW Mandiri",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    sub = parser.add_subparsers(dest="layer", required=True)

    # etl
    p_etl = sub.add_parser("etl", help="Benchmark ETL pipeline")
    p_etl.add_argument("--scale", required=True, help="Label skala: S / M / L / XL")
    p_etl.add_argument("--mode", default="full", choices=["full", "incremental"])

    # cube
    p_cube = sub.add_parser("cube", help="Benchmark cube build time + memory")
    p_cube.add_argument("--scale", required=True, help="Label skala: S / M / L / XL")
    p_cube.add_argument("--runs", type=int, default=3, help="Jumlah repetisi (default=3)")

    # query
    p_query = sub.add_parser("query", help="Benchmark OLAP query response time")
    p_query.add_argument("--scale", required=True, help="Label skala: S / M / L / XL")
    p_query.add_argument("--runs", type=int, default=30, help="Jumlah repetisi per query (default=30)")
    p_query.add_argument("--warmup", type=int, default=5, help="Jumlah warm-up run (default=5)")

    # quality
    sub.add_parser("quality", help="Hitung ETL data quality metrics")

    args = parser.parse_args()
    _ensure_results()

    if args.layer == "etl":
        run_etl(args.scale, args.mode)
    elif args.layer == "cube":
        run_cube(args.scale, n_runs=args.runs)
    elif args.layer == "query":
        run_query(args.scale, n_warmup=args.warmup, n_runs=args.runs)
    elif args.layer == "quality":
        run_quality()
