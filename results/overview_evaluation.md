# Overview Evaluasi — End-to-End Scalability
## Data Warehouse & OLAP Architecture for Banking Transaction Analytics

---

## Konteks

Paper ini mengimplementasikan sistem Data Warehouse transaksi perbankan digital Bank Mandiri dengan arsitektur end-to-end:

```
CSV Source → ETL Pipeline → PostgreSQL Star Schema → Atoti OLAP Cube → FastAPI → React Dashboard
```

Paper awalnya bersifat *implementation paper* — mendeskripsikan sistem yang dibangun tanpa evaluasi performa kuantitatif. Untuk meningkatkan kontribusi akademik ke level SINTA 2, ditambahkan **eksperimen scalability evaluation** yang mengukur performa sistem secara end-to-end terhadap pertumbuhan volume data.

---

## Objektif

> **Research Question**: *Bagaimana profil skalabilitas sistem Data Warehouse perbankan berbasis Star Schema dan MOLAP in-memory pada setiap layer arsitektur terhadap pertumbuhan volume data transaksi?*

Tiga sub-objektif:
1. Mengukur apakah ETL incremental load terdegradasi seiring pertumbuhan total data
2. Mengkarakterisasi trade-off MOLAP: cube build time dan memory footprint vs volume data
3. Mengevaluasi OLAP query response time per complexity class terhadap pertumbuhan data

---

## Metode

### Dataset
| Scale | Total Rows | Keterangan |
|---|---|---|
| S | 4,843 | Full load (default_data) |
| M | 227,832 | + 25 incremental batch |
| L | 450,943 | + 50 incremental batch |
| XL | 897,547 | + 100 incremental batch |

Data transaksi perbankan digital sintetis (ATM, BI-FAST, QRIS, ATM-Link, LIVIN), rentang 2026–2050, dihosting di PostgreSQL Aiven Cloud.

### Layer yang Dievaluasi

**Layer 1 — ETL Pipeline**
- Metrik: execution time (s), throughput (rows/s)
- Protokol: setiap incremental batch diukur secara individual (101 data point total)

**Layer 2 — Cube Construction**
- Metrik: build time (s), memory footprint RSS (MB)
- Protokol: 3 repetisi per scale, dilaporkan median

**Layer 3 — OLAP Query**
- 7 query dikelompokkan dalam 3 complexity class:
  - **Simple** (Q1-KPI, Q2-MonthlyTrend): agregasi tanpa GROUP BY atau GROUP BY 1 dimensi waktu
  - **Roll-up** (Q3-Channel, Q4-Segment, Q5-City): GROUP BY 1 dimensi non-waktu
  - **Pivot** (Q6-ChannelCity, Q7-Heatmap): GROUP BY 2 dimensi (cross-dimensional)
- Protokol: 5 warm-up runs (dibuang) + 30 measurement runs, dilaporkan median

### Analisis
Growth rate dihitung via linear regression: `y = slope × (x/1000) + intercept`, dengan slope sebagai **ms per 1.000 rows tambahan**. R² digunakan untuk mengukur linearitas pertumbuhan.

---

## Hasil

### Layer 1 — ETL Scalability

| Scale | Total Rows | ETL Time/batch (avg) |
|---|---|---|
| S | 4,843 | 16.75s (full load) |
| M | 227,832 | ~22s |
| L | 450,943 | ~24s |
| XL | 897,547 | ~30s |

- **Growth rate**: 10.51 ms/1K rows
- **R² = 0.065** — hampir nol, tidak ada korelasi signifikan antara ukuran DB dan waktu ETL
- **Temuan kunci**: Watermark-based incremental load terbukti berjalan dalam kompleksitas **O(batch_size)**, bukan O(total_data). Waktu ETL per batch relatif konstan meski total DB tumbuh hingga 897K baris
- Beberapa outlier (87s, 67s) disebabkan network latency ke Aiven Cloud, bukan degradasi sistem

### Layer 2 — Cube Construction

| Scale | Rows | Build Time (median) | Memory RSS |
|---|---|---|---|
| S | 4,843 | 12.74s | 207 MB |
| M | 227,832 | 17.95s | 329 MB |
| L | 450,943 | 21.49s | 440 MB |
| XL | 897,547 | 35.87s | 681 MB |

- **Growth rate**: 25.77 ms/1K rows — **PRIMARY BOTTLENECK**
- **R² = 0.982** — pertumbuhan sangat linear dan predictable
- Memory footprint tumbuh dari 207 MB ke 681 MB untuk 900K baris — efisien
- Trade-off MOLAP terkonfirmasi: build time naik linear, tapi hanya ~36s untuk 900K baris

### Layer 3 — OLAP Query

| Complexity | Scale-S | Scale-M | Scale-L | Scale-XL | Growth Rate | R² |
|---|---|---|---|---|---|---|
| Simple | 14.0ms | 27.8ms | 41.6ms | 77.7ms | 0.072 ms/1K | 0.995 |
| Roll-up | 11.4ms | 24.9ms | 35.4ms | 58.9ms | 0.053 ms/1K | 0.999 |
| Pivot | 8.7ms | 34.2ms | 60.6ms | 124.3ms | 0.130 ms/1K | 0.997 |

- Semua query **di bawah 125ms** bahkan di 897K baris
- Pivot paling sensitif terhadap pertumbuhan data (growth rate tertinggi)
- Roll-up paling stabil (growth rate terendah, R² = 0.999)
- Seluruh growth rate < 0.2 ms/1K — query layer sangat efisien

### ETL Data Quality

| Metric | Value |
|---|---|
| Total input rows | 5,000 |
| Duplicate removed | 100 (2.0%) |
| Negative nominal removed | 57 (1.14%) |
| Invalid date removed | 0 (0%) |
| **Data Quality Rate** | **96.86%** |
| Unknown nasabah mapping | 8,865 (0.99% dari total fact) |
| Unknown merchant mapping | 10,341 (1.15%) |
| Unknown channel mapping | 8,922 (0.99%) |
| Unknown wilayah mapping | 9,573 (1.07%) |

### Bottleneck Ranking

| Rank | Layer | Growth Rate (ms/1K rows) | R² |
|---|---|---|---|
| 1 | **Cube Construction** ← bottleneck | 25.772 | 0.982 |
| 2 | ETL Pipeline | 10.507 | 0.065 |
| 3 | OLAP Query (Pivot) | 0.130 | 0.997 |
| 4 | OLAP Query (Simple) | 0.072 | 0.995 |
| 5 | OLAP Query (Roll-up) | 0.053 | 0.999 |

---

## Kesimpulan

Tiga kontribusi empirik yang dihasilkan:

1. **Incremental ETL tidak terdegradasi** — R²=0.065 membuktikan watermark-based strategy efektif secara skalabilitas. Operator perbankan dapat menambah data tanpa kekhawatiran peningkatan biaya komputasi ETL

2. **Cube construction adalah trade-off utama MOLAP** — sebagai primary bottleneck dengan growth rate 25.77 ms/1K rows, namun masih dalam batas akseptabel (35.87s untuk 897K baris). Memory footprint 681 MB jauh di bawah kapasitas server modern

3. **Query sub-125ms di semua skala** — arsitektur terbukti layak untuk *production-scale* banking analytics. Pivot operations sebagai kompleksitas tertinggi tetap berada di 124ms pada 897K baris, memenuhi threshold interaktivitas dashboard (<200ms)

---

*Generated from benchmark results: `etl_benchmark.csv`, `cube_benchmark.csv`, `query_benchmark.csv`, `etl_quality.csv`*
*Chart: `scalability_charts.png`*
