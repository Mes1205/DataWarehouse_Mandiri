# Data Warehouse and OLAP Architecture for Banking Transaction Analytics

> Research implementation accompanying the paper:
> **"Scalability Evaluation of a MOLAP-Based Banking Analytics Architecture"**
> — submitted to RESTI (SINTA 2)

---

## Overview

This repository contains the full implementation of an end-to-end banking transaction analytics system, covering ETL pipeline, Star Schema Data Warehouse, in-memory MOLAP cube, RESTful API, and interactive dashboard. The system was developed as both a functional analytics platform and a research artifact for empirical scalability evaluation.

The evaluation examined system behavior across ETL execution, MOLAP cube construction, and analytical query processing layers using transaction datasets scaled from 4,843 to 897,547 records.

---

## Architecture

```
CSV Sources (dirty data)
        │
        ▼
ETL Pipeline (Python)
  Extract → Cleanse → Standardize → Surrogate Key Resolution → Load
        │
        ▼
PostgreSQL Data Warehouse (Aiven Cloud)
  Star Schema: fact_transaksi + 5 dimension tables
  Materialized View: mvw_dashboard_transaksi
        │
        ▼
Atoti MOLAP Cube (in-memory, JVM)
  Hierarchies: Time, Customer, Merchant, Channel, Geography
  Measures: Total Volume, Total Admin Fee, Count, Average
  Operations: Slice, Dice, Roll-up, Drill-down, Pivot
        │
        ▼
FastAPI Service Layer (14 analytical endpoints)
        │
        ▼
React Dashboard (Vite)
  12 chart components — KPI, trends, distributions, maps, heatmaps
```

---

## Key Results (Scalability Evaluation)

| Layer | Metric | Growth Rate | R² |
|---|---|---|---|
| ETL Pipeline | Execution Time | 10.51 ms / 1K rows | 0.065 |
| Cube Construction | Build Time | 25.77 ms / 1K rows | 0.982 |
| Cube Construction | Memory (RSS) | 0.53 MB / 1K rows | 0.9998 |
| Query — Simple | Response Time | 0.0716 ms / 1K rows | 0.995 |
| Query — Roll-up | Response Time | 0.0527 ms / 1K rows | 0.999 |
| Query — Pivot | Response Time | 0.1301 ms / 1K rows | 0.997 |

**Key findings:**
- Incremental ETL maintains stable performance regardless of warehouse size (R² = 0.065)
- All analytical queries remain below 150 ms at maximum scale (897,547 records)
- Cube reconstruction is the primary scalability bottleneck (R² = 0.982)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11, JavaScript (React) |
| Database | PostgreSQL (Aiven Cloud) |
| ETL & Processing | Pandas, SQLAlchemy |
| OLAP Engine | Atoti 0.9.15 (in-memory, requires Java 17) |
| Backend API | FastAPI, Uvicorn |
| Frontend | React, Vite, Recharts, Leaflet |
| Benchmark & Analysis | NumPy, Matplotlib, psutil |

---

## Project Structure

```
DataWarehouse_Mandiri/
├── main.py                  # ETL entry point (full / incremental)
├── config.py                # Database connection & configuration
├── requirements.txt
│
├── etl/                     # ETL modules
│   ├── dimensi.py           #   dimension ETL (full & incremental)
│   ├── fakta.py             #   fact ETL + materialized view
│   ├── common.py            #   shared CSV reader
│   └── wilayah_data.py      #   geographical reference data
│
├── analytics/
│   └── cube.py              # Atoti MOLAP cube construction
│
├── dashboard/
│   ├── backend/             # FastAPI + cube service
│   └── frontend/            # React + Vite dashboard
│
├── data/
│   ├── default_data/        # Initial dataset (full load)
│   └── generate1/           # 100 incremental batches
│
├── tools/
│   ├── generate_dirty_data.py   # Synthetic dirty data generator
│   ├── benchmark.py             # Scalability benchmark runner
│   ├── run_benchmark_auto.py    # Automated end-to-end benchmark
│   ├── analyze.py               # Regression analysis + charts
│   ├── plot_etl_scatter.py      # Figure 8 generator
│   ├── plot_cube_figures.py     # Figure 9 & 10 generator
│   ├── plot_query_figure.py     # Figure 11 generator
│   ├── plot_bottleneck_figure.py# Figure 12 generator
│   └── export_csv.py            # Star Schema CSV export
│
└── results/                 # Benchmark outputs (CSV, PNG, TXT)
```

---

## Getting Started

### Prerequisites

- Python **3.11**
- Java **17** (required by Atoti)
- Node.js **18+** and npm
- PostgreSQL instance (e.g., [Aiven](https://aiven.io/) free tier)

### 1. Setup Python Environment

```bash
python3.11 -m venv .venv_atoti
source .venv_atoti/bin/activate
pip install -r requirements.txt
pip install psutil matplotlib  # for benchmark tools
```

### 2. Configure Environment

Create `.env` in the project root:

```env
DB_URL=postgresql+psycopg2://<user>:<password>@<host>:<port>/<dbname>?sslmode=require
DATA_DIR=data/default_data
```

### 3. Run Initial ETL (Full Load)

```bash
python main.py full
```

### 4. Generate Incremental Batch Data

```bash
python tools/generate_dirty_data.py --batches 100
```

### 5. Run Dashboard

```bash
# Option A — single command
./run_dashboard.sh

# Option B — manual
# Terminal 1: Backend
cd dashboard/backend
source ../../.venv_atoti/bin/activate
export ATOTI_HIDE_EULA_MESSAGE=True
uvicorn main:app --port 8000

# Terminal 2: Frontend
cd dashboard/frontend
npm install
npm run dev
```

Open **http://localhost:5173**

---

## Running Incremental Loads

```bash
for i in $(seq -w 1 100); do
  DATA_DIR=data/generate1/batch_$(printf "%03d" $i) python main.py incremental
done
```

After loading new batches, click **"Refresh Data"** in the dashboard or call:

```bash
curl -X POST http://localhost:8000/api/cube/refresh
```

---

## Running the Scalability Benchmark

Automated end-to-end benchmark across 4 scales (S / M / L / XL):

```bash
source .venv_atoti/bin/activate
python tools/run_benchmark_auto.py
```

Results are saved to `results/`:

| File | Content |
|---|---|
| `etl_benchmark.csv` | ETL execution time per batch |
| `cube_benchmark.csv` | Cube build time + memory per scale |
| `query_benchmark.csv` | Query response time (30 runs × 7 queries × 4 scales) |
| `etl_quality.csv` | ETL data quality metrics |
| `benchmark_report.txt` | Full analysis report |
| `summary_*.csv` | Processed summary tables with growth rates |
| `scalability_charts.png` | All benchmark charts |

To regenerate analysis and charts from existing results:

```bash
python tools/analyze.py
```

---

## Exploring the OLAP Cube

```bash
source .venv_atoti/bin/activate
export ATOTI_HIDE_EULA_MESSAGE=True
python -m analytics.cube
```

Opens Atoti Web App for interactive pivot table exploration.

---

## Data Generation Details

The synthetic dataset simulates dirty banking transaction data with controlled error rates:

| Error Type | Rate |
|---|---|
| Duplicate transaction IDs | ~4% |
| Empty transaction dates | ~4% |
| Invalid date formats | ~3% |
| Negative nominal values | ~4% |
| Empty admin fees | ~5% |
| Unresolvable FK references | ~4% |

After ETL cleansing, the pipeline achieved a **data quality rate of 96.86%** on the initial dataset.

---

## Dataset Scale

| Scale | Fact Records | Source |
|---|---|---|
| Full Load (S) | 4,843 | `data/default_data/` |
| + 25 batches (M) | 227,832 | `data/generate1/batch_001–025` |
| + 50 batches (L) | 450,943 | `data/generate1/batch_001–050` |
| + 100 batches (XL) | 897,547 | `data/generate1/batch_001–100` |

---

## License

Built for academic research purposes.
