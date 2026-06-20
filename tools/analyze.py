# tools/analyze.py
# Baca hasil benchmark dari results/*.csv, hitung growth rate per layer,
# identifikasi bottleneck, cetak tabel, dan generate charts (jika matplotlib tersedia).
#
# Usage:
#   python tools/analyze.py
#
# Output:
#   - Tabel scalability per layer di terminal
#   - Bottleneck analysis (growth rate ranking)
#   - results/scalability_charts.png (jika matplotlib + numpy tersedia)

import contextlib
import csv
import io
import os
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(ROOT, "results")

# ── Optional deps ────────────────────────────────────────────────────────────
try:
    import numpy as np
    _HAS_NP = True
except ImportError:
    _HAS_NP = False

try:
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    _HAS_PLOT = True
except ImportError:
    _HAS_PLOT = False
    print("[WARN] matplotlib tidak tersedia — hanya tabel, tanpa chart.")
    print("       Install: pip install matplotlib")


# ── Helpers ──────────────────────────────────────────────────────────────────

SCALE_ORDER = ["S", "M", "L", "XL"]
SCALE_LABEL = {"S": "4K", "M": "51K", "L": "98K", "XL": "191K"}
COMPLEXITY_COLORS = {"simple": "#4C72B0", "rollup": "#DD8452", "pivot": "#55A868"}


def _read_csv(filename: str) -> list[dict]:
    path = os.path.join(RESULTS_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _sort_by_scale(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda r: SCALE_ORDER.index(r["scale"]))


def _growth_rate(x_rows: list, y_ms: list) -> tuple[float, float]:
    """
    Linear regression: y = slope * (x / 1000) + intercept
    Mengembalikan (slope_ms_per_1k_rows, R²).
    slope = berapa ms yang bertambah per 1.000 rows tambahan.
    """
    if not _HAS_NP or len(x_rows) < 2:
        return 0.0, 0.0
    x = np.array(x_rows, dtype=float) / 1000
    y = np.array(y_ms, dtype=float)
    coeffs  = np.polyfit(x, y, 1)
    slope   = coeffs[0]
    y_pred  = np.polyval(coeffs, x)
    ss_res  = np.sum((y - y_pred) ** 2)
    ss_tot  = np.sum((y - y.mean()) ** 2)
    r2      = 1 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return round(slope, 4), round(r2, 4)


def _hr(width: int = 60):
    print("─" * width)


# ── Layer 1: ETL ─────────────────────────────────────────────────────────────

def analyze_etl() -> float | None:
    data = _read_csv("etl_benchmark.csv")
    if not data:
        print("[ETL] Tidak ada data. Jalankan: python tools/benchmark.py etl --scale X --mode Y")
        return None

    print("\n" + "═" * 60)
    print("  LAYER 1 — ETL SCALABILITY")
    _hr()
    print(f"  {'Scale':<8} {'Rows':>10}  {'ETL Time (s)':>13}  {'Throughput (rows/s)':>20}")
    _hr()

    rows_list, time_ms_list = [], []
    for r in _sort_by_scale(data):
        n   = int(r["rows_total_in_db"])
        t   = float(r["etl_time_sec"])
        thr = float(r["throughput_rps"])
        print(f"  {r['scale']:<8} {n:>10,}  {t:>13.2f}  {thr:>20,.0f}")
        rows_list.append(n)
        time_ms_list.append(t * 1000)

    slope, r2 = _growth_rate(rows_list, time_ms_list)
    print(f"\n  Growth rate : {slope:.2f} ms per 1,000 rows")
    print(f"  R²          : {r2:.4f}")
    return slope


# ── Layer 2: Cube Build ──────────────────────────────────────────────────────

def analyze_cube() -> float | None:
    data = _read_csv("cube_benchmark.csv")
    if not data:
        print("[CUBE] Tidak ada data. Jalankan: python tools/benchmark.py cube --scale X")
        return None

    print("\n" + "═" * 60)
    print("  LAYER 2 — CUBE CONSTRUCTION SCALABILITY")
    _hr()
    print(f"  {'Scale':<8} {'Rows':>10}  {'Build Time (s)':>14}  {'Memory RSS (MB)':>16}")
    _hr()

    rows_list, time_ms_list = [], []
    for r in _sort_by_scale(data):
        n   = int(r["n_rows"])
        t   = float(r["median_build_sec"])
        mem = r["median_memory_mb"]
        print(f"  {r['scale']:<8} {n:>10,}  {t:>14.2f}  {str(mem):>16}")
        rows_list.append(n)
        time_ms_list.append(t * 1000)

    slope, r2 = _growth_rate(rows_list, time_ms_list)
    print(f"\n  Growth rate : {slope:.2f} ms per 1,000 rows")
    print(f"  R²          : {r2:.4f}")
    return slope


# ── Layer 3: OLAP Query ──────────────────────────────────────────────────────

def analyze_query() -> dict[str, float]:
    data = _read_csv("query_benchmark.csv")
    if not data:
        print("[QUERY] Tidak ada data. Jalankan: python tools/benchmark.py query --scale X")
        return {}

    print("\n" + "═" * 60)
    print("  LAYER 3 — OLAP QUERY SCALABILITY")

    slopes = {}
    for complexity in ["simple", "rollup", "pivot"]:
        subset  = [r for r in data if r["complexity"] == complexity]
        queries = list(dict.fromkeys(r["query"] for r in subset))

        print(f"\n  [{complexity.upper()}]  Queries: {', '.join(queries)}")
        _hr()

        # Header
        header = f"  {'Scale':<8} {'Rows':>10}"
        for q in queries:
            header += f"  {q:>16}"
        header += f"  {'Avg (ms)':>10}"
        print(header)
        _hr()

        # Kelompokkan per scale
        by_scale: dict[str, dict] = {}
        for r in subset:
            sc = r["scale"]
            if sc not in by_scale:
                by_scale[sc] = {"n_rows": int(r["n_rows"]), "times": {}}
            by_scale[sc]["times"][r["query"]] = float(r["median_ms"])

        rows_list, avg_ms_list = [], []
        for sc in SCALE_ORDER:
            if sc not in by_scale:
                continue
            entry = by_scale[sc]
            times = [entry["times"].get(q, 0.0) for q in queries]
            avg   = sum(times) / len(times) if times else 0.0

            line = f"  {sc:<8} {entry['n_rows']:>10,}"
            for t in times:
                line += f"  {t:>16.2f}"
            line += f"  {avg:>10.2f}"
            print(line)

            rows_list.append(entry["n_rows"])
            avg_ms_list.append(avg)

        slope, r2 = _growth_rate(rows_list, avg_ms_list)
        print(f"\n  Growth rate : {slope:.4f} ms per 1,000 rows  (R²={r2:.4f})")
        slopes[complexity] = slope

    return slopes


# ── Bottleneck Analysis ──────────────────────────────────────────────────────

def analyze_bottleneck(etl_slope, cube_slope, query_slopes: dict):
    print("\n" + "═" * 60)
    print("  BOTTLENECK ANALYSIS — Growth Rate Ranking")
    _hr()
    print(f"  {'Layer':<28} {'Growth Rate (ms/1K rows)':>25}")
    _hr()

    all_layers: dict[str, float] = {}
    if etl_slope  : all_layers["ETL Pipeline"]           = etl_slope
    if cube_slope : all_layers["Cube Construction"]      = cube_slope
    for c, s in (query_slopes or {}).items():
        all_layers[f"OLAP Query ({c})"] = s

    ranked = sorted(all_layers.items(), key=lambda x: x[1], reverse=True)
    for i, (layer, slope) in enumerate(ranked):
        tag = "  ← PRIMARY BOTTLENECK" if i == 0 else ""
        print(f"  {layer:<28} {slope:>25.4f}{tag}")

    if ranked:
        bottleneck = ranked[0][0]
        print(f"\n  Kesimpulan: {bottleneck} menunjukkan pertumbuhan latency")
        print(f"  tertinggi dan merupakan bottleneck utama arsitektur ini.")


# ── ETL Quality Summary ──────────────────────────────────────────────────────

def analyze_quality():
    data = _read_csv("etl_quality.csv")
    if not data:
        print("[QUALITY] Tidak ada data. Jalankan: python tools/benchmark.py quality")
        return

    r = data[0]
    print("\n" + "═" * 60)
    print("  ETL DATA QUALITY METRICS")
    _hr()
    print(f"  Total input rows         : {int(r['total_input_rows']):>10,}")
    print(f"  Duplicate removed        : {int(r['duplicate_removed']):>10,}")
    print(f"  Negative nominal removed : {int(r['negative_nominal_removed']):>10,}")
    print(f"  Invalid date removed     : {int(r['invalid_date_removed']):>10,}")
    print(f"  Total removed            : {int(r['total_records_removed']):>10,}")
    print(f"  ─────────────────────────────────────────────")
    print(f"  Data Quality Rate        : {r['data_quality_rate_pct']:>9}%")
    print(f"  ─────────────────────────────────────────────")
    print(f"  Unknown nasabah mapping  : {int(r['unknown_nasabah']):>10,}")
    print(f"  Unknown merchant mapping : {int(r['unknown_merchant']):>10,}")
    print(f"  Unknown channel mapping  : {int(r['unknown_channel']):>10,}")
    print(f"  Unknown wilayah mapping  : {int(r['unknown_wilayah']):>10,}")
    print(f"  ─────────────────────────────────────────────")
    print(f"  Fact rows in DB          : {int(r['fact_rows_in_db']):>10,}")


# ── Charts ───────────────────────────────────────────────────────────────────

def generate_charts(etl_data, cube_data, query_data):
    if not _HAS_PLOT or not _HAS_NP:
        print("\n[CHART] Dilewati — install matplotlib dan numpy untuk generate chart.")
        return

    fig = plt.figure(figsize=(16, 10))
    fig.suptitle(
        "End-to-End Scalability Evaluation\nData Warehouse Mandiri — Banking Transaction Analytics",
        fontsize=13, fontweight="bold", y=0.98,
    )
    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.45, wspace=0.35)

    x_labels = [SCALE_LABEL[s] for s in SCALE_ORDER]

    # ── Chart 1: ETL Time ────────────────────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, 0])
    if etl_data:
        sorted_etl = _sort_by_scale(etl_data)
        x = [SCALE_LABEL[r["scale"]] for r in sorted_etl]
        y = [float(r["etl_time_sec"]) for r in sorted_etl]
        ax1.plot(x, y, marker="o", color="#4C72B0", linewidth=2, markersize=7)
        ax1.fill_between(range(len(x)), y, alpha=0.1, color="#4C72B0")
        for i, (xi, yi) in enumerate(zip(x, y)):
            ax1.annotate(f"{yi:.1f}s", (xi, yi), textcoords="offset points",
                         xytext=(0, 8), ha="center", fontsize=8)
    ax1.set_title("Layer 1: ETL Execution Time", fontweight="bold", fontsize=10)
    ax1.set_xlabel("Data Volume (rows)")
    ax1.set_ylabel("Time (s)")
    ax1.grid(True, alpha=0.3)

    # ── Chart 2: Cube Build Time ─────────────────────────────────────────────
    ax2 = fig.add_subplot(gs[0, 1])
    if cube_data:
        sorted_cube = _sort_by_scale(cube_data)
        x = [SCALE_LABEL[r["scale"]] for r in sorted_cube]
        y = [float(r["median_build_sec"]) for r in sorted_cube]
        ax2.plot(x, y, marker="s", color="#DD8452", linewidth=2, markersize=7)
        ax2.fill_between(range(len(x)), y, alpha=0.1, color="#DD8452")
        for xi, yi in zip(x, y):
            ax2.annotate(f"{yi:.1f}s", (xi, yi), textcoords="offset points",
                         xytext=(0, 8), ha="center", fontsize=8)
    ax2.set_title("Layer 2: Cube Build Time", fontweight="bold", fontsize=10)
    ax2.set_xlabel("Data Volume (rows)")
    ax2.set_ylabel("Median Build Time (s)")
    ax2.grid(True, alpha=0.3)

    # ── Chart 3: Memory Usage ────────────────────────────────────────────────
    ax3 = fig.add_subplot(gs[0, 2])
    if cube_data:
        sorted_cube = _sort_by_scale(cube_data)
        x   = [SCALE_LABEL[r["scale"]] for r in sorted_cube]
        mem = [r["median_memory_mb"] for r in sorted_cube]
        if all(m != "N/A" for m in mem):
            y = [float(m) for m in mem]
            ax3.bar(x, y, color="#55A868", alpha=0.8, edgecolor="white")
            for xi, yi in zip(x, y):
                ax3.annotate(f"{yi:.0f}MB", (xi, yi), textcoords="offset points",
                             xytext=(0, 4), ha="center", fontsize=8)
        else:
            ax3.text(0.5, 0.5, "psutil not available\nNo memory data",
                     transform=ax3.transAxes, ha="center", va="center",
                     fontsize=10, color="gray")
    ax3.set_title("Layer 2: Memory Footprint", fontweight="bold", fontsize=10)
    ax3.set_xlabel("Data Volume (rows)")
    ax3.set_ylabel("RSS Memory (MB)")
    ax3.grid(True, alpha=0.3, axis="y")

    # ── Chart 4: Query Response Time per Complexity ──────────────────────────
    ax4 = fig.add_subplot(gs[1, :2])
    if query_data:
        by_complexity: dict[str, dict] = {}
        for r in query_data:
            c  = r["complexity"]
            sc = r["scale"]
            if c not in by_complexity:
                by_complexity[c] = {}
            if sc not in by_complexity[c]:
                by_complexity[c][sc] = []
            by_complexity[c][sc].append(float(r["median_ms"]))

        for complexity, by_scale in by_complexity.items():
            x, y = [], []
            for sc in SCALE_ORDER:
                if sc in by_scale:
                    x.append(SCALE_LABEL[sc])
                    times = by_scale[sc]
                    y.append(sum(times) / len(times))
            ax4.plot(x, y, marker="o", linewidth=2, markersize=7,
                     color=COMPLEXITY_COLORS.get(complexity, "gray"),
                     label=complexity.capitalize())

    ax4.set_title("Layer 3: OLAP Query Response Time by Complexity Class",
                  fontweight="bold", fontsize=10)
    ax4.set_xlabel("Data Volume (rows)")
    ax4.set_ylabel("Avg Median Time (ms)")
    ax4.legend(title="Complexity")
    ax4.grid(True, alpha=0.3)

    # ── Chart 5: Bottleneck Bar (Growth Rate) ────────────────────────────────
    ax5 = fig.add_subplot(gs[1, 2])
    etl_data_csv   = _read_csv("etl_benchmark.csv")
    cube_data_csv  = _read_csv("cube_benchmark.csv")
    query_data_csv = _read_csv("query_benchmark.csv")

    slopes = {}

    def _get_slope(data_csv, time_col, mul=1000):
        if not data_csv:
            return None
        sorted_d = _sort_by_scale(data_csv)
        rows = [int(r.get("rows_total_in_db", r.get("n_rows", 0))) for r in sorted_d]
        ms   = [float(r[time_col]) * mul for r in sorted_d]
        s, _ = _growth_rate(rows, ms)
        return s

    s_etl  = _get_slope(etl_data_csv,  "etl_time_sec", mul=1000)
    s_cube = _get_slope(cube_data_csv, "median_build_sec", mul=1000)
    if s_etl  : slopes["ETL"]        = s_etl
    if s_cube : slopes["Cube Build"] = s_cube

    if query_data_csv:
        for complexity in ["simple", "rollup", "pivot"]:
            subset = [r for r in query_data_csv if r["complexity"] == complexity]
            by_scale = {}
            for r in subset:
                sc = r["scale"]
                if sc not in by_scale:
                    by_scale[sc] = {"n": int(r["n_rows"]), "t": []}
                by_scale[sc]["t"].append(float(r["median_ms"]))
            rows_l = [by_scale[sc]["n"] for sc in SCALE_ORDER if sc in by_scale]
            avg_l  = [sum(by_scale[sc]["t"]) / len(by_scale[sc]["t"])
                      for sc in SCALE_ORDER if sc in by_scale]
            s, _ = _growth_rate(rows_l, avg_l)
            slopes[f"Query\n({complexity})"] = s

    if slopes:
        labels = list(slopes.keys())
        values = [slopes[l] for l in labels]
        colors = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B2"]
        bars   = ax5.barh(labels, values,
                          color=colors[:len(labels)], alpha=0.85, edgecolor="white")
        ax5.bar_label(bars, fmt="%.3f", padding=4, fontsize=8)
        # Highlight bottleneck
        max_idx = values.index(max(values))
        bars[max_idx].set_edgecolor("red")
        bars[max_idx].set_linewidth(2)

    ax5.set_title("Bottleneck Analysis\n(Growth Rate ms / 1K rows)",
                  fontweight="bold", fontsize=10)
    ax5.set_xlabel("ms per 1,000 rows")
    ax5.grid(True, alpha=0.3, axis="x")
    ax5.invert_yaxis()

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    out_path = os.path.join(RESULTS_DIR, "scalability_charts.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"\n[CHART] Saved → {out_path}")
    plt.show()


# ── Summary CSV Export ───────────────────────────────────────────────────────

def save_summary_csvs():
    """Export tabel hasil analisis ke results/summary_*.csv."""

    # summary_etl.csv
    etl_data = _read_csv("etl_benchmark.csv")
    if etl_data:
        rows_l, ms_l = [], []
        out = []
        for r in _sort_by_scale(etl_data):
            n = int(r["rows_total_in_db"])
            t = float(r["etl_time_sec"])
            rows_l.append(n); ms_l.append(t * 1000)
            out.append({
                "scale": r["scale"],
                "rows_total": n,
                "etl_time_sec": t,
                "throughput_rps": float(r["throughput_rps"]),
            })
        if _HAS_NP and len(rows_l) >= 2:
            slope, r2 = _growth_rate(rows_l, ms_l)
            for row in out:
                row["growth_rate_ms_per_1k"] = slope
                row["r2"] = r2
        path = os.path.join(RESULTS_DIR, "summary_etl.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=out[0].keys())
            w.writeheader(); w.writerows(out)
        print(f"[CSV] Saved → {path}")

    # summary_cube.csv
    cube_data = _read_csv("cube_benchmark.csv")
    if cube_data:
        rows_l, ms_l = [], []
        out = []
        for r in _sort_by_scale(cube_data):
            n = int(r["n_rows"])
            t = float(r["median_build_sec"])
            rows_l.append(n); ms_l.append(t * 1000)
            out.append({
                "scale": r["scale"],
                "n_rows": n,
                "median_build_sec": t,
                "min_build_sec": float(r["min_build_sec"]),
                "max_build_sec": float(r["max_build_sec"]),
                "median_memory_mb": r["median_memory_mb"],
            })
        if _HAS_NP and len(rows_l) >= 2:
            slope, r2 = _growth_rate(rows_l, ms_l)
            for row in out:
                row["growth_rate_ms_per_1k"] = slope
                row["r2"] = r2
        path = os.path.join(RESULTS_DIR, "summary_cube.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=out[0].keys())
            w.writeheader(); w.writerows(out)
        print(f"[CSV] Saved → {path}")

    # summary_query.csv
    query_data = _read_csv("query_benchmark.csv")
    if query_data:
        out = []
        for complexity in ["simple", "rollup", "pivot"]:
            subset = [r for r in query_data if r["complexity"] == complexity]
            by_scale = {}
            for r in subset:
                sc = r["scale"]
                if sc not in by_scale:
                    by_scale[sc] = {"n_rows": int(r["n_rows"]), "times": []}
                by_scale[sc]["times"].append(float(r["median_ms"]))

            rows_l, avg_l = [], []
            for sc in SCALE_ORDER:
                if sc not in by_scale:
                    continue
                entry = by_scale[sc]
                avg = sum(entry["times"]) / len(entry["times"])
                rows_l.append(entry["n_rows"]); avg_l.append(avg)
                out.append({
                    "scale": sc,
                    "n_rows": entry["n_rows"],
                    "complexity": complexity,
                    "avg_median_ms": round(avg, 3),
                })

            if _HAS_NP and len(rows_l) >= 2:
                slope, r2 = _growth_rate(rows_l, avg_l)
                for row in out:
                    if row["complexity"] == complexity:
                        row["growth_rate_ms_per_1k"] = slope
                        row["r2"] = r2

        if out:
            path = os.path.join(RESULTS_DIR, "summary_query.csv")
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=out[0].keys())
                w.writeheader(); w.writerows(out)
            print(f"[CSV] Saved → {path}")

    # summary_bottleneck.csv
    all_layers = {}
    if etl_data and _HAS_NP:
        rows_l = [int(r["rows_total_in_db"]) for r in _sort_by_scale(etl_data)]
        ms_l   = [float(r["etl_time_sec"]) * 1000 for r in _sort_by_scale(etl_data)]
        s, r2  = _growth_rate(rows_l, ms_l)
        all_layers["ETL Pipeline"] = {"growth_rate_ms_per_1k": s, "r2": r2}
    if cube_data and _HAS_NP:
        rows_l = [int(r["n_rows"]) for r in _sort_by_scale(cube_data)]
        ms_l   = [float(r["median_build_sec"]) * 1000 for r in _sort_by_scale(cube_data)]
        s, r2  = _growth_rate(rows_l, ms_l)
        all_layers["Cube Construction"] = {"growth_rate_ms_per_1k": s, "r2": r2}
    if query_data and _HAS_NP:
        for complexity in ["simple", "rollup", "pivot"]:
            subset = [r for r in query_data if r["complexity"] == complexity]
            by_sc  = {}
            for r in subset:
                sc = r["scale"]
                if sc not in by_sc:
                    by_sc[sc] = {"n": int(r["n_rows"]), "t": []}
                by_sc[sc]["t"].append(float(r["median_ms"]))
            rows_l = [by_sc[sc]["n"] for sc in SCALE_ORDER if sc in by_sc]
            avg_l  = [sum(by_sc[sc]["t"]) / len(by_sc[sc]["t"])
                      for sc in SCALE_ORDER if sc in by_sc]
            if len(rows_l) >= 2:
                s, r2 = _growth_rate(rows_l, avg_l)
                all_layers[f"OLAP Query ({complexity})"] = {
                    "growth_rate_ms_per_1k": s, "r2": r2
                }

    if all_layers:
        ranked = sorted(all_layers.items(),
                        key=lambda x: x[1]["growth_rate_ms_per_1k"], reverse=True)
        out = [
            {
                "rank": i + 1,
                "layer": layer,
                "growth_rate_ms_per_1k": v["growth_rate_ms_per_1k"],
                "r2": v["r2"],
                "is_bottleneck": i == 0,
            }
            for i, (layer, v) in enumerate(ranked)
        ]
        path = os.path.join(RESULTS_DIR, "summary_bottleneck.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=out[0].keys())
            w.writeheader(); w.writerows(out)
        print(f"[CSV] Saved → {path}")


# ── Tee: tulis ke terminal + file sekaligus ───────────────────────────────────

class _Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for s in self.streams:
            s.write(data)

    def flush(self):
        for s in self.streams:
            s.flush()


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    txt_path = os.path.join(RESULTS_DIR, "benchmark_report.txt")
    os.makedirs(RESULTS_DIR, exist_ok=True)

    with open(txt_path, "w", encoding="utf-8") as f:
        header = (
            f"BENCHMARK REPORT — Data Warehouse Mandiri\n"
            f"Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"{'=' * 60}\n"
        )
        f.write(header)
        print(header, end="")

        tee = _Tee(sys.stdout, f)
        with contextlib.redirect_stdout(tee):
            etl_slope    = analyze_etl()
            cube_slope   = analyze_cube()
            query_slopes = analyze_query()
            analyze_bottleneck(etl_slope, cube_slope, query_slopes)
            analyze_quality()

    print(f"\n[REPORT] Saved → {txt_path}")

    save_summary_csvs()

    etl_raw   = _read_csv("etl_benchmark.csv")
    cube_raw  = _read_csv("cube_benchmark.csv")
    query_raw = _read_csv("query_benchmark.csv")
    generate_charts(etl_raw, cube_raw, query_raw)
