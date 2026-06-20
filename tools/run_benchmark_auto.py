# tools/run_benchmark_auto.py
# Automated end-to-end benchmark runner.
#
# Alur otomatis:
#   1. Full load (default_data) → benchmark ETL + Cube + Query  [Scale-S]
#   2. Incremental batch_001..025 (masing-masing timed) → Cube + Query  [Scale-M]
#   3. Incremental batch_026..050 → Cube + Query  [Scale-L]
#   4. Incremental batch_051..100 → Cube + Query  [Scale-XL]
#   5. Jalankan analyze.py → tabel + chart siap
#
# Usage:
#   source .venv_atoti/bin/activate
#   python tools/run_benchmark_auto.py
#
# Estimasi waktu: 2-4 jam (mayoritas dari query benchmark 30 runs × 7 query × 4 skala)
# Semua hasil disimpan ke results/*.csv — aman dijalankan ulang (append).

import os
import subprocess
import sys
import time
from datetime import datetime

ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON = sys.executable

# ── Konfigurasi skala benchmark ──────────────────────────────────────────────
# Format: (label, batch_start, batch_end)
# batch_start=0 → full load dari default_data
# batch_start>0 → jalankan incremental dari batch_start sampai batch_end

CHECKPOINTS = [
    ("S",   0,    0),   # Full load only          → ~5K rows
    ("M",   1,   25),   # + batch_001..025         → ~235K rows
    ("L",  26,   50),   # + batch_026..050         → ~470K rows
    ("XL", 51,  100),   # + batch_051..100         → ~935K rows
]

DEFAULT_DATA_DIR  = os.path.join(ROOT, "data", "default_data")
GENERATE_DATA_DIR = os.path.join(ROOT, "data", "generate1")


# ── Helpers ───────────────────────────────────────────────────────────────────

def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"\n[{ts}] {msg}")
    sys.stdout.flush()


def run(cmd: list, data_dir: str = None, check: bool = True) -> int:
    """Jalankan subprocess. data_dir di-set sebagai env var DATA_DIR."""
    env = os.environ.copy()
    env["ATOTI_HIDE_EULA_MESSAGE"] = "True"
    if data_dir:
        env["DATA_DIR"] = data_dir
    result = subprocess.run(cmd, env=env, cwd=ROOT)
    if check and result.returncode != 0:
        print(f"\n[ERROR] Command gagal (exit {result.returncode}): {' '.join(cmd)}")
        sys.exit(result.returncode)
    return result.returncode


def benchmark_cmd(*args) -> list:
    return [PYTHON, "tools/benchmark.py"] + list(args)


def eta_str(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}h {m}m {s}s" if h else f"{m}m {s}s"


# ── Fase 1: Full Load → Scale-S ───────────────────────────────────────────────

def phase_full_load():
    log("=" * 60)
    log("PHASE 1 — Full Load + Benchmark Scale-S")
    log("=" * 60)

    log("Menjalankan ETL full load (default_data)...")
    run(benchmark_cmd("etl", "--scale", "S", "--mode", "full"),
        data_dir=DEFAULT_DATA_DIR)

    log("Benchmark Cube Build — Scale-S")
    run(benchmark_cmd("cube", "--scale", "S"))

    log("Benchmark OLAP Query — Scale-S (30 runs × 7 query)")
    run(benchmark_cmd("query", "--scale", "S"))

    log("Scale-S selesai ✓")


# ── Fase 2-4: Incremental Batches → Scale-M, L, XL ──────────────────────────

def phase_incremental(scale: str, batch_start: int, batch_end: int):
    log("=" * 60)
    log(f"PHASE — Incremental batch_{batch_start:03d}..{batch_end:03d} → Scale-{scale}")
    log("=" * 60)

    n_batches = batch_end - batch_start + 1

    for batch_num in range(batch_start, batch_end + 1):
        batch_label = f"batch_{batch_num:03d}"
        data_dir    = os.path.join(GENERATE_DATA_DIR, batch_label)

        log(f"  ETL Incremental — {batch_label} ({batch_num - batch_start + 1}/{n_batches})")
        run(
            benchmark_cmd("etl", "--scale", scale, "--mode", "incremental"),
            data_dir=data_dir,
        )

    log(f"Benchmark Cube Build — Scale-{scale}")
    run(benchmark_cmd("cube", f"--scale", scale))

    log(f"Benchmark OLAP Query — Scale-{scale} (30 runs × 7 query)")
    run(benchmark_cmd("query", "--scale", scale))

    log(f"Scale-{scale} selesai ✓")


# ── Fase Akhir: ETL Quality + Analyze ────────────────────────────────────────

def phase_quality():
    log("=" * 60)
    log("PHASE — ETL Quality Metrics (default_data)")
    log("=" * 60)
    run(benchmark_cmd("quality"), data_dir=DEFAULT_DATA_DIR)
    log("ETL quality selesai ✓")


def phase_analyze():
    log("=" * 60)
    log("PHASE — Analisis & Generate Charts")
    log("=" * 60)
    run([PYTHON, "tools/analyze.py"])
    log("Analisis selesai ✓")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    t_global = time.perf_counter()

    print("\n" + "█" * 60)
    print("  AUTO BENCHMARK — Data Warehouse Mandiri")
    print(f"  Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("█" * 60)

    print("\nCheckpoint plan:")
    for label, b_start, b_end in CHECKPOINTS:
        if b_start == 0:
            desc = "full load"
        else:
            desc = f"batch_{b_start:03d} → batch_{b_end:03d} ({b_end - b_start + 1} batches)"
        print(f"  Scale-{label:<3} : {desc}")

    print("\nStarting in 3 seconds... (Ctrl+C untuk cancel)")
    time.sleep(3)

    # Jalankan semua fase sesuai checkpoint
    for i, (scale, batch_start, batch_end) in enumerate(CHECKPOINTS):
        t_phase = time.perf_counter()

        if batch_start == 0:
            phase_full_load()
        else:
            phase_incremental(scale, batch_start, batch_end)

        elapsed = time.perf_counter() - t_phase
        remaining = len(CHECKPOINTS) - i - 1
        log(f"Phase Scale-{scale} done dalam {eta_str(elapsed)} "
            f"({remaining} phase tersisa)")

    # Quality + Analyze
    phase_quality()
    phase_analyze()

    total = time.perf_counter() - t_global
    print("\n" + "█" * 60)
    print(f"  BENCHMARK SELESAI dalam {eta_str(total)}")
    print(f"  End: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Hasil: results/etl_benchmark.csv")
    print(f"         results/cube_benchmark.csv")
    print(f"         results/query_benchmark.csv")
    print(f"         results/etl_quality.csv")
    print(f"         results/scalability_charts.png")
    print("█" * 60)


if __name__ == "__main__":
    main()
