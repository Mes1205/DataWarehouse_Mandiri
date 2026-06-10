# 🏦 DataWarehouse Mandiri

**Data Warehouse end-to-end** untuk transaksi perbankan digital — mencakup
ETL (Extract, Transform, Load), Star Schema di PostgreSQL, OLAP Cube
in-memory (Atoti), dan Dashboard analitik interaktif (FastAPI + React).

> Dibangun untuk mendemonstrasikan alur lengkap data warehouse: dari data
> mentah yang "kotor" hingga visualisasi business intelligence yang siap
> pakai — termasuk simulasi *slicing, dicing, drill-down, roll-up,* dan
> *pivot* secara nyata di atas data transaksi.

---

## ✨ Fitur Utama

- **Pipeline ETL lengkap** (`main.py`) dengan dua mode:
  - `full` — truncate & reload semua data dari awal
  - `incremental` — hanya memuat data baru (berbasis watermark)
- **Star Schema** di PostgreSQL: 1 tabel fakta + 5 tabel dimensi, dengan
  penanganan data kotor (format tidak konsisten, nilai kosong, duplikat,
  dsb.) dan fallback "Unknown" untuk menjaga integritas referensial.
- **Materialized View** siap pakai untuk BI tools eksternal (mis. Looker
  Studio).
- **OLAP Cube in-memory (Atoti)** dengan hierarchies & measures custom —
  mendukung query analitik cepat tanpa JOIN berulang ke database.
- **Dashboard interaktif** (React + Vite) dengan 12+ visualisasi: KPI,
  tren bulanan, distribusi channel/segmen/gender, peta sebaran transaksi,
  ranking kota & merchant, heatmap, dan lainnya.
- **Filter global** (slice & dice) yang memengaruhi seluruh dashboard
  sekaligus, plus tombol **Refresh Data** untuk rebuild cube tanpa restart
  backend.
- **ETL Monitor** — visualisasi simulasi alur pipeline ETL step-by-step
  dengan live log, untuk keperluan edukasi/presentasi.
- **Generator data dummy** untuk mensimulasikan pertumbuhan data secara
  bertahap (incremental load).

---

## 🏗️ Arsitektur

```
┌──────────────┐    ┌────────────────┐    ┌──────────────────┐
│  CSV Sumber  │ -> │  ETL (Python)  │ -> │  PostgreSQL       │
│ (data kotor) │    │  etl/*.py      │    │  Star Schema +    │
└──────────────┘    │  main.py       │    │  Materialized View│
                     └────────────────┘    └─────────┬─────────┘
                                                       │
                                                       v
                                            ┌──────────────────┐
                                            │  Atoti OLAP Cube  │
                                            │  analytics/cube.py│
                                            │  (in-memory)      │
                                            └─────────┬─────────┘
                                                       │
                                  ┌────────────────────┴────────────────────┐
                                  v                                          v
                        ┌──────────────────┐                    ┌──────────────────────┐
                        │ FastAPI Backend   │ <----- HTTP -----> │ React Frontend (Vite) │
                        │ dashboard/backend │                    │ dashboard/frontend    │
                        └──────────────────┘                    └──────────────────────┘
```

Penjelasan detail tiap komponen, skema database, dan operasi OLAP
(slice/dice/drill-down/roll-up/pivot) tersedia di **[dokumentasi.md](dokumentasi.md)**.

---

## 📁 Struktur Proyek

```
DataWarehouse_Mandiri/
├── main.py              # Entry point pipeline ETL (full / incremental)
├── config.py            # Koneksi database & konfigurasi
├── requirements.txt      # Dependency Python
├── run_dashboard.sh       # Script untuk menjalankan dashboard sekaligus
├── etl/                   # Modul ETL (dimensi, fakta, helper)
├── analytics/             # OLAP Cube (Atoti)
├── data/                  # Dataset (default & batch incremental)
├── tools/                 # Generator data & utilitas export
└── dashboard/
    ├── backend/           # FastAPI (API + cube service + ETL monitor)
    └── frontend/          # React + Vite (UI dashboard)
```

---

## 🛠️ Tech Stack

| Layer | Teknologi |
|---|---|
| Bahasa | Python 3.11, JavaScript (React) |
| Database | PostgreSQL (Aiven Cloud) |
| ETL & Data Processing | Pandas, SQLAlchemy |
| OLAP Engine | [Atoti](https://www.atoti.io/) (in-memory cube, butuh Java 17) |
| Backend API | FastAPI, Uvicorn |
| Frontend | React, Vite, Recharts, Leaflet |

---

## 🚀 Memulai (Getting Started)

### 1. Prasyarat

- Python **3.11**
- Java **17** (dibutuhkan oleh Atoti)
- Node.js **18+** & npm
- Akses ke database PostgreSQL (mis. [Aiven](https://aiven.io/))

### 2. Setup Environment Python

```bash
python3.11 -m venv .venv_atoti
source .venv_atoti/bin/activate
pip install -r requirements.txt
```

### 3. Konfigurasi `.env`

Buat file `.env` di root proyek:

```env
DB_URL=postgresql+psycopg2://<user>:<password>@<host>:<port>/<dbname>?sslmode=require
DATA_DIR=data/default_data
```

### 4. Jalankan ETL (Load Data Pertama Kali)

```bash
python3 main.py full
```

Perintah di atas akan membuat & mengisi seluruh tabel star schema beserta
materialized view.

### 5. Jalankan Dashboard

Cara termudah — satu perintah untuk backend (cube + API) dan frontend:

```bash
./run_dashboard.sh
```

Lalu buka **http://localhost:5173** di browser.

<details>
<summary>Atau jalankan manual (backend & frontend terpisah)</summary>

```bash
# Terminal 1 — Backend
cd dashboard/backend
source ../../.venv_atoti/bin/activate
export ATOTI_HIDE_EULA_MESSAGE=True
uvicorn main:app --port 8000

# Terminal 2 — Frontend
cd dashboard/frontend
npm install   # sekali saja
npm run dev
```
</details>

---

## 🔄 Simulasi Incremental Load

Generate data tambahan (20 batch) untuk mensimulasikan data baru yang masuk
secara berkala:

```bash
python3 tools/generate_dirty_data.py
```

Lalu muat tiap batch secara berurutan:

```bash
DATA_DIR=data/generate1/batch_01 python3 main.py incremental
DATA_DIR=data/generate1/batch_02 python3 main.py incremental
# ... dst sampai batch_20
```

Setelah itu, klik tombol **"Refresh Data"** di dashboard (atau panggil
`POST /api/cube/refresh`) agar cube & visualisasi menampilkan data terbaru
tanpa perlu restart backend.

---

## 📊 Eksplorasi OLAP Cube Mandiri

```bash
source .venv_atoti/bin/activate
export ATOTI_HIDE_EULA_MESSAGE=True
python -m analytics.cube
```

Akan membuka Atoti Web App untuk eksplorasi pivot table interaktif
(drag-and-drop) langsung di browser.

---

## 📖 Dokumentasi Lengkap

Untuk penjelasan **end-to-end** mengenai:
- Alur generate data & jenis "data kotor" yang ditangani
- Detail proses ETL (dimensi & fakta, full vs incremental)
- Skema database (ER diagram & deskripsi kolom)
- OLAP Cube: hierarchies, measures, serta contoh konkret operasi
  **slice, dice, roll-up, drill-down, dan pivot**
- Pemetaan setiap chart dashboard ke endpoint & operasi OLAP
- Referensi fungsi setiap file dalam proyek

➡️ Lihat **[dokumentasi.md](dokumentasi.md)**

---

## 📄 Lisensi

Proyek ini dibuat untuk keperluan pembelajaran/akademik.
