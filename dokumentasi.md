# Dokumentasi Proyek — Data Warehouse Mandiri

Dokumentasi ini menjelaskan **end-to-end** proyek Data Warehouse (DW) Mandiri:
mulai dari data sumber (CSV) → proses ETL → Star Schema di PostgreSQL →
Materialized View → OLAP Cube (Atoti) → Dashboard interaktif (FastAPI +
React).

---

## Daftar Isi

1. [Gambaran Umum Proyek](#1-gambaran-umum-proyek)
2. [Struktur Folder Proyek](#2-struktur-folder-proyek)
3. [Referensi Lengkap Setiap File](#3-referensi-lengkap-setiap-file)
4. [Tahap 1 — Data Generation (Sumber Data)](#4-tahap-1--data-generation-sumber-data)
5. [Tahap 2 — Proses ETL](#5-tahap-2--proses-etl)
6. [Skema Database — Star Schema](#6-skema-database--star-schema)
7. [Tahap 3 — OLAP Cube (Atoti)](#7-tahap-3--olap-cube-atoti)
8. [Tahap 4 — Dashboard (Backend + Frontend)](#8-tahap-4--dashboard-backend--frontend)
9. [ETL Monitor — Simulasi Visual Pipeline](#9-etl-monitor--simulasi-visual-pipeline)
10. [Tools Pendukung](#10-tools-pendukung)
11. [Konfigurasi (`config.py` & `.env`)](#11-konfigurasi-configpy--env)
12. [Alur End-to-End Ringkas (Cheat Sheet)](#12-alur-end-to-end-ringkas-cheat-sheet)

---

## 1. Gambaran Umum Proyek

Proyek ini mensimulasikan sebuah **Data Warehouse transaksi perbankan**
(channel digital seperti ATM, BI-FAST, QRIS, ATM Link, LIVIN), mulai dari:

1. **Data sumber mentah** (CSV dari sistem operasional/CRM/MMS — sengaja
   dibuat "kotor": format tidak konsisten, ada yang kosong, ada duplikat).
2. **ETL (Extract, Transform, Load)** — membersihkan, menstandarkan, dan
   memuat data ke skema bintang (star schema) di PostgreSQL.
3. **Star Schema** — 1 tabel fakta (`fact_transaksi`) + 5 tabel dimensi
   (`dim_waktu`, `dim_nasabah`, `dim_merchant`, `dim_channel`, `dim_wilayah`).
4. **Materialized View** — view denormalisasi (`mvw_dashboard_transaksi`)
   untuk konsumsi BI tool seperti Looker Studio.
5. **OLAP Cube (Atoti)** — cube in-memory yang melakukan JOIN & agregasi
   (SUM, COUNT, AVG) di memori, dipakai sebagai sumber data dashboard.
6. **Dashboard** — backend FastAPI yang query ke cube, dan frontend React
   (Vite) yang menampilkan KPI, chart, peta, dan ETL Monitor (simulasi).

### Diagram Alur Besar

```
┌──────────────┐    ┌────────────────┐    ┌──────────────────┐
│  CSV Sumber  │ -> │  ETL (Python)  │ -> │  PostgreSQL       │
│ (kotor/dirty)│    │  etl/*.py      │    │  Star Schema      │
└──────────────┘    │  main.py       │    │  + Materialized   │
                     └────────────────┘    │    View           │
                                            └─────────┬─────────┘
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
                        │ FastAPI Backend   │                    │ React Frontend (Vite) │
                        │ dashboard/backend │ <----- HTTP -----> │ dashboard/frontend    │
                        └──────────────────┘                    └──────────────────────┘
```

---

## 2. Struktur Folder Proyek

```
DataWarehouse_Mandiri/
├── main.py                     # Entry point pipeline ETL (full / incremental)
├── config.py                   # Koneksi DB (Aiven PostgreSQL) & DATA_DIR
├── .env                         # DB_URL, DATA_DIR (TIDAK di-commit, berisi kredensial)
├── dokumentasi.md               # Dokumentasi ini
│
├── etl/                         # Modul ETL
│   ├── __init__.py
│   ├── common.py                #   helper baca CSV (auto-detect separator)
│   ├── dimensi.py                #   ETL 5 tabel dimensi (full & incremental)
│   ├── fakta.py                  #   ETL tabel fakta + materialized view
│   └── wilayah_data.py           #   data referensi kota/provinsi/region + mapping
│
├── analytics/
│   ├── __init__.py
│   └── cube.py                  # Bangun OLAP Cube (Atoti) dari Star Schema
│
├── data/
│   ├── default_data/            # Dataset awal (baseline, full load)
│   │   ├── dim_waktu_clean.csv  #   kalender 2001-01-01 s/d 2030-12-31
│   │   ├── nasabah_crm.csv      #   1000 nasabah
│   │   ├── merchant_mms.csv     #   100 merchant
│   │   └── transaksi_raw.csv    #   5000 transaksi (2026-01-01 s/d 2026-04-11)
│   └── generate1/                # Dataset lanjutan (untuk simulasi incremental)
│       └── batch_01 .. batch_20/
│           ├── nasabah_crm.csv
│           ├── merchant_mms.csv
│           └── transaksi_raw.csv
│
├── tools/
│   ├── __init__.py
│   ├── generate_dirty_data.py   # Generator data dummy "kotor" (batch incremental)
│   └── export_csv.py            # Export isi tabel Star Schema -> CSV (backup)
│
└── dashboard/
    ├── backend/                  # FastAPI
    │   ├── main.py               #   route/endpoint API
    │   ├── cube_service.py       #   wrapper query ke Atoti cube
    │   └── etl_runner.py         #   simulasi visual ETL Monitor
    └── frontend/                 # React + Vite
        └── src/
            ├── main.jsx           # entry point React
            ├── App.jsx            # routing (Dashboard / ETL Monitor)
            ├── api.js             # axios client ke backend
            ├── utils/format.js    # helper format angka/currency
            ├── context/FilterContext.jsx
            ├── hooks/useCubeQuery.js
            ├── components/        # FilterBar, KPI, charts, ETL pipeline UI
            └── pages/              # DashboardPage, EtlMonitorPage
```

---

## 3. Referensi Lengkap Setiap File

Tabel berikut menjelaskan **fungsi setiap file** dalam proyek, dikelompokkan
per folder.

### 3.1 Root

| File | Fungsi |
|---|---|
| `main.py` | Entry point pipeline ETL. Argumen `full` (default, truncate + load semua) atau `incremental` (load data baru saja). Memanggil fungsi-fungsi di `etl/dimensi.py` & `etl/fakta.py` secara berurutan, lalu `create_materialized_view()`. |
| `config.py` | Pusat konfigurasi: load `.env`, expose `DB_URL`, `DATA_DIR`, dan `get_engine()` (SQLAlchemy engine ke PostgreSQL Aiven) — dipakai oleh semua modul ETL, `analytics/cube.py`, dan `tools/`. |
| `.env` | File kredensial (tidak di-commit ke git) — berisi `DB_URL` (connection string Postgres) & `DATA_DIR` (folder sumber CSV aktif). |
| `dokumentasi.md` | Dokumentasi proyek (file ini). |

### 3.2 `etl/` — Modul ETL

| File | Fungsi |
|---|---|
| `etl/__init__.py` | Penanda package Python (kosong). |
| `etl/common.py` | Helper `_read_source_csv(filename)` — baca CSV dari `DATA_DIR`, auto-deteksi separator `;`/`,`, return `None` jika file tidak ada. |
| `etl/dimensi.py` | ETL untuk 5 tabel dimensi: `_transform_dimensi()` (extract+transform semua dimensi), `run_dimensi()` (full load), `run_dimensi_incremental()` (insert baris baru saja via `_append_new_rows`). |
| `etl/fakta.py` | ETL untuk `fact_transaksi`: `_transform_fakta()` (extract+transform+lookup surrogate key), `run_fakta()` (full load), `run_fakta_incremental()` (insert berdasarkan watermark `MAX(waktu_id)`), `create_materialized_view()` (build `mvw_dashboard_transaksi`). |
| `etl/wilayah_data.py` | Data referensi statis (tanpa dependency DB): `MAP_KOTA` (normalisasi singkatan kota), `KOTA_INFO`/`MAP_PROV`/`MAP_REGION` (kota → provinsi/region), `ALL_KOTA` (master list 16 kota). Dipakai bersama oleh `dimensi.py`, `fakta.py`, dan `generate_dirty_data.py`. |

### 3.3 `analytics/` — OLAP Cube

| File | Fungsi |
|---|---|
| `analytics/__init__.py` | Penanda package Python (kosong). |
| `analytics/cube.py` | `_load_star_schema()` (baca 6 tabel dari Postgres ke pandas), `build_cube()` (bangun atoti `Session` + `Cube`, definisikan hierarchies & measures), `run_sample_queries()` (contoh query OLAP: KPI, channel, segmentasi, dst). Bisa dijalankan mandiri (`python -m analytics.cube`) untuk membuka Atoti Web App. |

### 3.4 `data/` — Dataset

| File/Folder | Fungsi |
|---|---|
| `data/default_data/dim_waktu_clean.csv` | Kalender harian 2001-01-01 s/d 2030-12-31 (10.957 baris), sudah bersih — sumber `dim_waktu`. |
| `data/default_data/nasabah_crm.csv` | 1.000 data nasabah awal (kode `N-10001`..`N-11000`), sumber `dim_nasabah`. |
| `data/default_data/merchant_mms.csv` | 100 data merchant awal (kode `MCH-5001`..`MCH-5100`), sumber `dim_merchant`. |
| `data/default_data/transaksi_raw.csv` | 5.000 transaksi awal (Jan–Apr 2026, kode `TRX-200001`..`TRX-204999`), sumber `fact_transaksi` & ekstraksi `dim_channel`/`dim_wilayah`. Dipakai untuk **Full Load** pertama. |
| `data/generate1/batch_01..batch_20/*.csv` | 20 batch data lanjutan (nasabah/merchant/transaksi baru, tanggal transaksi maju & tidak overlap), masing-masing dipakai sebagai `DATA_DIR` untuk satu kali `python main.py incremental`. |

### 3.5 `tools/` — Script Pendukung

| File | Fungsi |
|---|---|
| `tools/__init__.py` | Penanda package Python (kosong). |
| `tools/generate_dirty_data.py` | Generator data dummy "kotor" — membuat 20 batch CSV lanjutan di `data/generate1/` untuk simulasi incremental load (lihat bagian 4.2). |
| `tools/export_csv.py` | Export seluruh tabel Star Schema dari PostgreSQL ke CSV di `output_csv/` (backup/inspeksi manual). |

### 3.6 `dashboard/backend/` — FastAPI

| File | Fungsi |
|---|---|
| `dashboard/backend/main.py` | Aplikasi FastAPI utama (`app = FastAPI(...)`). Mendaftarkan semua endpoint `/api/*` (KPI, chart, filter options, ETL monitor, cube refresh) dan CORS middleware. Cube di-build sekali saat startup (`_warm_up_cube`). |
| `dashboard/backend/cube_service.py` | Wrapper query ke Atoti cube: `get_cube()`/`refresh_cube()` (singleton + rebuild), `build_filter()` (translate query params → kondisi Atoti), `_df()` (helper `cube.query`), serta satu fungsi `get_*` per chart (KPI, monthly trend, channel distribution, dst). Juga berisi `CITY_COORDS` (lat/lon untuk peta). |
| `dashboard/backend/etl_runner.py` | **Simulasi** visual pipeline ETL untuk halaman ETL Monitor — TIDAK menjalankan ETL/DB sungguhan. Berisi `FULL_STEPS`/`INCREMENTAL_STEPS` (daftar tahapan), `SIM_LOGS_FULL`/`SIM_LOGS_INCREMENTAL` (log tiruan), `_run_simulation()` (jalan di thread, update status step demi step), `start_etl()`/`get_state()` (API untuk `main.py`). |

### 3.7 `dashboard/frontend/src/` — React + Vite

| File | Fungsi |
|---|---|
| `main.jsx` | Entry point React — render `<App />` ke DOM. |
| `App.jsx` | Routing aplikasi (`react-router-dom`): `/` → `DashboardPage`, `/etl` → `EtlMonitorPage`. Render `AppHeader` di semua halaman. |
| `App.css` | Style global aplikasi (layout shell, variabel warna `--accent`, dll). |
| `api.js` | Axios client ke backend (`http://127.0.0.1:8000/api`). Semua fungsi fetch (`getKpi`, `getMonthlyTrend`, dst), `getFilterOptions`, `refreshCube`, `runEtl`, `getEtlStatus`. Menangani serialisasi array filter sebagai repeated query param. |
| `utils/format.js` | Helper format angka: `formatNumber`, `formatCompactNumber`, `formatCurrencyTooltip`, `CHART_COLORS` (palet warna chart). |
| `context/FilterContext.jsx` | State filter global (tahun, quarter, bulan, channel, segmen, kategori, provinsi, kota, rentang tanggal, `include_unknown`) via React Context. Menyediakan `setFilter`, `resetFilters`, `hasActiveFilters`, serta `refreshAll()`/`refreshKey`/`isRefreshing` untuk fitur Refresh Data. |
| `hooks/useCubeQuery.js` | Hook generik `useCubeQuery(fetchFn, extraParams)` — panggil `fetchFn({...filters, ...extraParams})`, otomatis re-fetch saat `filters` atau `refreshKey` berubah. Return `{ data, loading }`. |
| `components/AppHeader.jsx` | Header aplikasi: judul, navigasi (Dashboard / ETL Monitor), badge "Live OLAP". |
| `components/ChartCard.jsx` + `.css` | Komponen wrapper kartu (judul, subtitle, animasi fade-in) dipakai oleh semua chart & KPI. |
| `components/FilterBar.jsx` + `.css` | UI filter global: dropdown multi-select (Tahun, Quarter, Bulan, Channel, Segmen, Kategori, Provinsi, Kota), input rentang tanggal, checkbox "Tampilkan data Unknown", tombol **Refresh Data** & **Reset Filter**. |
| `components/MultiSelectDropdown.jsx` + `.css` | Komponen dropdown multi-pilih reusable (dipakai FilterBar). |
| `components/KpiCard.jsx` + `.css` | Satu kartu KPI (angka animasi, format currency/compact, indikator trend naik/turun). |
| `components/KpiCards.jsx` | Container 4 `KpiCard` (Total Volume, Frekuensi, Revenue/Biaya Admin, Rata-rata Nominal) — ambil data dari `/api/kpi`. |
| `components/charts/MonthlyTrendChart.jsx` | Line chart tren transaksi bulanan (atau harian jika drill-down) — `/api/monthly-trend`. |
| `components/charts/ChannelDistributionChart.jsx` | Donut chart distribusi volume per channel — `/api/channel-distribution`. |
| `components/charts/CustomerSegmentChart.jsx` | Donut chart distribusi volume per segmen nasabah — `/api/customer-segment`. |
| `components/charts/GenderDistributionChart.jsx` | Donut chart distribusi volume per jenis kelamin — `/api/gender-distribution`. |
| `components/charts/MerchantCategoryChart.jsx` | Bar chart ranking kategori merchant — `/api/merchant-category`. |
| `components/charts/TopMerchantsTable.jsx` + `.css` | Tabel top-N merchant (sortable) — `/api/top-merchants`. |
| `components/charts/GeographicMap.jsx` | Peta interaktif (Leaflet) sebaran transaksi per kota — `/api/geographic`. |
| `components/charts/CityRankingChart.jsx` | Bar chart ranking kota by volume — `/api/city-ranking`. |
| `components/charts/ChannelByRegionChart.jsx` | Stacked bar chart penggunaan channel per kota — `/api/channel-by-region`. |
| `components/charts/DailyTransactionChart.jsx` | Bar chart jumlah transaksi per hari (Senin–Minggu) — `/api/daily-transaction`. |
| `components/charts/HeatmapChart.jsx` + `.css` | Heatmap Bulan x Hari (jumlah transaksi) — `/api/heatmap`. |
| `components/charts/DonutChart.jsx` | Komponen donut chart generik (dipakai Channel/Segment/Gender chart). |
| `components/etl/EtlPipeline.jsx` | Visualisasi step-by-step pipeline ETL (status pending/running/success/error per step, dikelompokkan per group). |
| `components/etl/EtlLogConsole.jsx` | Console log live (auto-scroll) untuk simulasi ETL. |
| `components/etl/Etl.css` | Style untuk halaman & komponen ETL Monitor. |
| `pages/DashboardPage.jsx` | Halaman utama — wrap `FilterProvider`, render `FilterBar`, `KpiCards`, dan grid semua chart. |
| `pages/EtlMonitorPage.jsx` | Halaman "ETL Monitor" — pilih mode (full/incremental), tombol "Jalankan Simulasi", tampilkan `EtlPipeline` & `EtlLogConsole` via SSE. |

---

## 4. Tahap 1 — Data Generation (Sumber Data)

### 4.1 `data/default_data/` — Dataset Baseline

Ini adalah data awal yang dipakai untuk **Full Load** pertama kali. Berisi:

| File | Jumlah Baris | Keterangan |
|---|---|---|
| `dim_waktu_clean.csv` | 10.957 | Kalender harian **2001-01-01 s/d 2030-12-31**, sudah bersih (siap pakai langsung sebagai dim_waktu) |
| `nasabah_crm.csv` | 1.000 | Data nasabah dari sistem CRM (kode `N-10001` s/d `N-11000`) |
| `merchant_mms.csv` | 100 | Data merchant dari sistem MMS (kode `MCH-5001` s/d `MCH-5100`) |
| `transaksi_raw.csv` | 5.000 | Transaksi mentah, tanggal **2026-01-01 s/d 2026-04-11**, kode `TRX-200001` s/d `TRX-204999` |

Format kolom mentah (separator `;`):

- **`nasabah_crm.csv`**: `nasabah_code;nama_lengkap;jenis_kelamin;tanggal_lahir;segmen_nasabah`
- **`merchant_mms.csv`**: `merchant_code;nama_merchant;kategori`
- **`transaksi_raw.csv`**: `trx_id;tgl_transaksi;nasabah_code;channel;merchant_code;kota;nominal;biaya_admin`
- **`dim_waktu_clean.csv`**: `waktu_id;tanggal;hari;bulan;tahun;quarter` (sudah bersih, langsung di-load apa adanya)

Data ini sudah **disengaja "kotor"** di beberapa kolom (lihat detail tipe
"kotor" di bagian 4.2) supaya pipeline ETL punya sesuatu untuk dibersihkan —
tapi tetap diberi rentang tanggal yang valid (Jan–Apr 2026) sebagai "data
historis awal".

### 4.2 `tools/generate_dirty_data.py` — Generator Data Lanjutan (Incremental)

Script ini men-generate **20 batch** data baru (`data/generate1/batch_01` s/d
`batch_20`) yang **melanjutkan** kode dari `default_data`:

| Entitas | Kode lanjutan | Per batch |
|---|---|---|
| Nasabah | `N-11001` dst | 1.000 baris/batch |
| Merchant | `MCH-5101` dst | 100 baris/batch |
| Transaksi | `TRX-205000` dst | 10.000 baris/batch (+ ~2% duplikat) |

**Kenapa dipecah jadi 20 batch?**
Supaya bisa mensimulasikan proses **incremental load** yang dijalankan
berulang kali (`python main.py incremental`), satu batch = satu kali "hari
operasional baru" yang datanya masuk ke DW.

**Tanggal transaksi per batch dibuat berurutan & TIDAK overlap**
(`split_date_range()`), membagi rentang `2026-04-12` s/d `2030-12-31` jadi 20
rentang berurutan. Ini PENTING karena `run_fakta_incremental()` (lihat bagian
5) memakai *watermark* `MAX(waktu_id)` — kalau tanggal antar batch acak/​
overlap, batch berikutnya bisa "tidak punya data baru" karena semua tanggalnya
sudah di bawah watermark batch sebelumnya.

#### Jenis "kotor" yang di-generate & cara ETL menanganinya

| Kolom | Variasi "kotor" | Ditangani di | Hasil akhir |
|---|---|---|---|
| `jenis_kelamin` | `L, P, M, Laki-laki, Female, Pria, Wanita, ''` | `etl/dimensi.py` (`map_jk` + `fillna('U')`) | `L` / `P` / `U` |
| `segmen_nasabah` | `Reguler, Prioritas, RETAIL, prio, Private, ''` | `etl/dimensi.py` (`fillna('Reguler')` + `replace`) | `Reguler` / `Prioritas` / `Private` |
| `tanggal_lahir` | kosong, atau `31/02/1999` (invalid) | `etl/dimensi.py` (`pd.to_datetime(..., errors='coerce')`) | tanggal valid atau `NaT` (NULL) |
| `kategori` (merchant) | `Retail, F&B, Food & Beverage, Health, Kesehatan, Market, Electronics, ''` | `etl/dimensi.py` (`fillna('Unknown')`) | kategori asli atau `Unknown` |
| `channel` | `ATM, BI_FAST, BIFAST, bifast, QRIS, qris, ATM_LINK, LIVIN, livin` | `etl/fakta.py` (`map_channel`, uppercase) | `ATM / BI_FAST / QRIS / ATM_LINK / LIVIN` |
| `kota` | nama lengkap + singkatan `BDG, Jkt Sel, SBY` | `etl/wilayah_data.py` (`MAP_KOTA`) | nama kota baku |
| `tgl_transaksi` | ~2% kosong, ~2% format invalid (`31-13-2026`) | `etl/fakta.py` (`pd.to_datetime(..., errors='coerce')`, baris di-drop) | tanggal valid (baris invalid dibuang) |
| `nominal` | format Indonesia (`1.000.000`, kadang `,xx` desimal), ~3% negatif | `etl/fakta.py` (bersihkan separator, `nominal < 0` dibuang) | angka numerik valid |
| `biaya_admin` | ~5% kosong | `etl/fakta.py` (`fillna(0)`) | angka (0 jika kosong) |
| `trx_id` | ~2% duplikat | `etl/fakta.py` (`drop_duplicates(subset='trx_id')`) | unik |
| `nasabah_code` / `merchant_code` / `channel` / `kota` | **~2% (UNKNOWN_RATE)** baris sengaja punya **salah satu** dari 4 kolom ini kosong | `etl/dimensi.py` & `etl/fakta.py` (fallback ke baris **"Unknown" id=0**) | join gagal -> diarahkan ke baris dimensi `Unknown` |

> **Filosofi desain**: hanya kombinasi *natural key kosong* (nasabah_code,
> merchant_code, channel, kota) yang benar-benar berakhir sebagai "Unknown"
> (FK id=0) — dan itu pun dibatasi ~2% dari total transaksi. Variasi penulisan
> lain (singkatan kota, alias channel, dsb) **selalu berhasil dipetakan**
> ke nilai yang valid, jadi tidak menambah jumlah "Unknown".

#### Cara menjalankan generator

```bash
python3 tools/generate_dirty_data.py
# opsional: --batches, --n-nasabah, --n-merchant, --n-transaksi, --seed, dst.
```

Output: `data/generate1/batch_01/` … `batch_20/`, masing-masing berisi
`nasabah_crm.csv`, `merchant_mms.csv`, `transaksi_raw.csv` (TANPA
`dim_waktu_clean.csv` — kalender sudah lengkap di `default_data` untuk
2001-2030, jadi tidak perlu digenerate ulang).

---

## 5. Tahap 2 — Proses ETL

### 5.1 Entry Point — `main.py`

```bash
python3 main.py            # mode "full"  (default)
python3 main.py incremental
```

| Mode | Langkah |
|---|---|
| **full** | 1. `truncate_semua_tabel()` — TRUNCATE semua tabel (RESTART IDENTITY CASCADE)<br>2. `run_dimensi()` — isi 5 tabel dimensi dari awal<br>3. `run_fakta()` — isi `fact_transaksi` dari awal<br>4. `create_materialized_view()` |
| **incremental** | 1. `run_dimensi_incremental()` — insert hanya baris dimensi dengan natural key baru<br>2. `run_fakta_incremental()` — insert hanya transaksi dengan `waktu_id` > watermark terakhir<br>3. `create_materialized_view()` |

Sumber data ditentukan oleh **`DATA_DIR`** di `.env` (lihat `config.py`).
Untuk load incremental per batch, override via env var tanpa edit `.env`:

```bash
DATA_DIR=data/generate1/batch_01 python3 main.py incremental
DATA_DIR=data/generate1/batch_02 python3 main.py incremental
# ... dst, harus berurutan batch_01 -> batch_20
```

### 5.2 `etl/common.py` — Helper Baca CSV

`_read_source_csv(filename)`:
- Baca file dari `DATA_DIR` (return `None` jika tidak ada — sehingga satu
  folder `DATA_DIR` boleh hanya berisi sebagian file).
- **Auto-detect separator** `;` atau `,` dari baris header.

### 5.3 `etl/dimensi.py` — ETL 5 Tabel Dimensi

Fungsi `_transform_dimensi()` melakukan EXTRACT + TRANSFORM untuk 5 dimensi:

1. **`dim_waktu`** — dibaca langsung dari `dim_waktu_clean.csv` (tidak perlu
   transformasi tambahan, sudah bersih).

2. **`dim_nasabah`** — dari `nasabah_crm.csv`:
   - Standarisasi `jenis_kelamin` → `L` / `P` / `U` (default jika tidak dikenal)
   - Parse `tanggal_lahir` (format `dd/mm/yyyy`, `errors='coerce'` → `NaT` jika invalid)
   - Standarisasi `segmen_nasabah` → `Reguler` / `Prioritas` / nilai asli lain
   - Surrogate key `nasabah_id` mulai dari 1
   - **+1 baris fallback "Unknown" (id=0)**

3. **`dim_merchant`** — dari `merchant_mms.csv`:
   - `kategori` kosong → `Unknown`
   - Surrogate key `merchant_id` mulai dari 1
   - **+1 baris fallback "Unknown Merchant" (id=0)**

4. **`dim_channel`** — diekstrak dari **kolom `channel` di `transaksi_raw.csv`**
   (bukan dari file master tersendiri):
   - Uppercase + normalisasi (`BIFAST` → `BI_FAST`)
   - Ambil nilai unik → jadi daftar channel
   - Surrogate key `channel_id` mulai dari 1
   - **+1 baris fallback "UNKNOWN" (id=0)**

5. **`dim_wilayah`** — diekstrak dari **kolom `kota` di `transaksi_raw.csv`**,
   digabung dengan **master list `ALL_KOTA`** (lihat `etl/wilayah_data.py`):
   - Normalisasi singkatan kota via `MAP_KOTA` (BDG → Bandung, dst.)
   - Gabungkan dengan `ALL_KOTA` (16 kota se-Indonesia) supaya `dim_wilayah`
     selalu lengkap walau belum ada transaksi untuk kota tsb.
   - Tambah `provinsi` & `region` via `MAP_PROV` / `MAP_REGION`
   - Surrogate key `wilayah_id` mulai dari 1
   - **+1 baris fallback "Unknown" (id=0)**

#### Mode FULL — `run_dimensi()`
Insert semua baris (dipakai setelah TRUNCATE).

#### Mode INCREMENTAL — `run_dimensi_incremental()`
Untuk tiap dimensi, panggil `_append_new_rows(df, engine, table, id_col, key_col)`:
- Baca natural key (`key_col`) yang sudah ada di DB.
- Filter `df` → hanya baris dengan natural key **belum ada** di DB.
- Surrogate key (`id_col`) baris baru melanjutkan dari `MAX(id_col)` di DB.
- Insert baris baru saja (idempotent — aman dijalankan berulang).

| Tabel | id_col | key_col (natural key) |
|---|---|---|
| dim_waktu | waktu_id | waktu_id |
| dim_nasabah | nasabah_id | nasabah_code |
| dim_merchant | merchant_id | merchant_code |
| dim_channel | channel_id | nama_channel |
| dim_wilayah | wilayah_id | kota |

### 5.4 `etl/fakta.py` — ETL Tabel Fakta + Materialized View

Fungsi `_transform_fakta(engine)`:

1. **EXTRACT**: baca `transaksi_raw.csv` + baca surrogate key dari
   `dim_nasabah`, `dim_merchant`, `dim_channel`, `dim_wilayah` (yang sudah
   ter-load di DB).

2. **TRANSFORM**:
   - `drop_duplicates(subset='trx_id')` — buang duplikat transaksi
   - Bersihkan `nominal` (hapus titik ribuan, ganti koma desimal → titik) →
     numerik; `biaya_admin` → numerik, `fillna(0)`
   - Buang baris `nominal < 0`
   - Buat `waktu_id` (format `YYYYMMDD`) dari `tgl_transaksi`
     (`dayfirst=True`, `errors='coerce'`); baris dengan tanggal invalid
     **di-drop**
   - Normalisasi `channel` via `map_channel` (BIFAST→BI_FAST, dst), nilai
     tak dikenal → `UNKNOWN`
   - Normalisasi `kota` via `MAP_KOTA`, nilai kosong → `Unknown`
   - `nasabah_code` / `merchant_code` kosong → `UNKNOWN` / `MCH-UNKNOWN`

3. **LOOKUP / JOIN** (natural key → surrogate key, `how='left'`):
   - `nasabah_code` → `nasabah_id`
   - `merchant_code` → `merchant_id`
   - `channel_bersih` → `channel_id` (via `nama_channel`)
   - `kota_bersih` → `wilayah_id` (via `kota`)
   - Hasil join `NaN` (gagal) → `fillna(0)` → mengarah ke baris **Unknown**
     id=0 di dimensi terkait.

4. **VALIDASI**: pastikan `waktu_id` ada di `dim_waktu` (FK). Jika tidak,
   baris di-drop (di-print sebagai warning).

5. **FINALISASI**: kolom akhir = `waktu_id, nasabah_id, channel_id,
   wilayah_id, merchant_id, nominal_transaksi, biaya_admin`.

#### Mode FULL — `run_fakta()`
- `fact_id` dibuat berurut mulai dari 1.
- Insert semua baris.

#### Mode INCREMENTAL — `run_fakta_incremental()`
- Ambil **watermark**: `MAX(waktu_id)` & `MAX(fact_id)` dari `fact_transaksi` saat ini.
- Filter hanya baris dengan `waktu_id > watermark_waktu`.
- `fact_id` baris baru melanjutkan dari `MAX(fact_id) + 1`.
- Jika tidak ada baris baru → cetak `"Tidak ada transaksi baru"` & selesai.

> **Catatan penting**: pendekatan watermark tanggal berarti transaksi
> *late-arriving* (tanggal lama yang baru masuk belakangan) **tidak akan
> ter-capture**. Inilah alasan generator data (`generate_dirty_data.py`)
> dibuat dengan tanggal **maju & tidak overlap** per batch.

#### `create_materialized_view()`
- `DROP MATERIALIZED VIEW IF EXISTS mvw_dashboard_transaksi`
- `CREATE MATERIALIZED VIEW ... AS SELECT ...` — JOIN `fact_transaksi` dengan
  semua dimensi, hasilkan satu baris per transaksi dengan semua atribut
  deskriptif (nama nasabah, segmen, channel, kota, provinsi, merchant,
  kategori, tanggal, bulan, tahun, nominal, biaya admin).
- Dipakai sebagai sumber data untuk **Looker Studio** (BI tool eksternal,
  query langsung tanpa JOIN kompleks).
- Dijalankan dengan `AUTOCOMMIT` karena `CREATE MATERIALIZED VIEW` tidak bisa
  di dalam transaksi eksplisit di PostgreSQL.

### 5.5 `etl/wilayah_data.py` — Data Referensi Wilayah

Modul tanpa dependency database (stdlib saja), dipakai bersama oleh
`etl/dimensi.py`, `etl/fakta.py`, dan `tools/generate_dirty_data.py`:

- **`MAP_KOTA`** — normalisasi singkatan kota:
  ```python
  {'BDG': 'Bandung', 'Jkt Sel': 'Jakarta Selatan', 'SBY': 'Surabaya'}
  ```
- **`KOTA_INFO`** — 16 kota se-Indonesia → `(provinsi, region/pulau)`,
  mencakup Jawa, Sumatera, Kalimantan, Sulawesi, Bali & Nusa Tenggara, Papua.
- **`MAP_PROV`**, **`MAP_REGION`** — turunan dari `KOTA_INFO`.
- **`ALL_KOTA`** — daftar 16 kota baku (dipakai untuk pre-populate `dim_wilayah`).

---

## 6. Skema Database — Star Schema

Skema bintang dengan 1 tabel fakta di tengah & 5 tabel dimensi mengelilinginya.
**Catatan**: FK secara fisik **tidak di-enforce** sebagai constraint di
PostgreSQL (tidak ada `FOREIGN KEY` di DDL) — integritas referensial dijaga
secara **logis oleh ETL** (setiap dimensi punya baris fallback `id=0`
"Unknown" sehingga JOIN dari fakta selalu menemukan pasangan).

### 6.1 Diagram Star Schema

```
                    ┌────────────────┐
                    │   dim_waktu     │
                    │ waktu_id (PK)   │
                    │ tanggal         │
                    │ hari            │
                    │ bulan           │
                    │ tahun           │
                    │ quarter         │
                    └────────┬────────┘
                             │
┌────────────────┐          │          ┌──────────────────┐
│  dim_nasabah    │          │          │   dim_channel     │
│ nasabah_id (PK) │          │          │ channel_id (PK)   │
│ nasabah_code    │          │          │ nama_channel      │
│ nama_lengkap    │          │          │ jenis_channel     │
│ jenis_kelamin   │          │          └─────────┬─────────┘
│ tanggal_lahir   │\         │         /
│ segmen_nasabah  │ \        │        /
└────────┬────────┘  \       │       /
         │            \      │      /
         │             v     v     v
         │           ┌──────────────────────┐
         └---------->│   fact_transaksi      │<----------┐
                      │ fact_id (PK)          │           │
                      │ waktu_id (FK)         │           │
                      │ nasabah_id (FK)       │           │
                      │ channel_id (FK)       │           │
                      │ wilayah_id (FK)       │           │
                      │ merchant_id (FK)      │           │
                      │ nominal_transaksi     │           │
                      │ biaya_admin           │           │
                      └──────────┬────────────┘           │
                                  │                        │
                    /-------------+                        │
                   v                                       │
        ┌──────────────────┐                  ┌────────────────────┐
        │   dim_wilayah     │                  │   dim_merchant      │
        │ wilayah_id (PK)   │                  │ merchant_id (PK)    │
        │ kota              │                  │ merchant_code       │
        │ provinsi          │                  │ nama_merchant       │
        │ region            │                  │ kategori            │
        └───────────────────┘                  └─────────────────────┘
                                                            ^
                                                            └---------- (FK dari fact_transaksi)
```

### 6.2 Detail Kolom Tiap Tabel (DB Aktual)

#### `dim_waktu`
| Kolom | Tipe | Keterangan |
|---|---|---|
| waktu_id | bigint | PK, format `YYYYMMDD` (mis. `20260411`) |
| tanggal | text | `YYYY-MM-DD` |
| hari | text | nama hari (Inggris): `Monday` … `Sunday` |
| bulan | text | nama bulan (Inggris): `January` … `December` |
| tahun | bigint | tahun (2001–2030) |
| quarter | text | `Q1`–`Q4` |

#### `dim_nasabah`
| Kolom | Tipe | Keterangan |
|---|---|---|
| nasabah_id | bigint | PK (0 = Unknown) |
| nasabah_code | text | natural key, mis. `N-10001` |
| nama_lengkap | text | |
| jenis_kelamin | text | `L` / `P` / `U` |
| tanggal_lahir | date | bisa `NULL` jika sumber invalid |
| segmen_nasabah | text | `Reguler` / `Prioritas` / `Private` / dll |

#### `dim_merchant`
| Kolom | Tipe | Keterangan |
|---|---|---|
| merchant_id | bigint | PK (0 = Unknown) |
| merchant_code | text | natural key, mis. `MCH-5001` |
| nama_merchant | text | |
| kategori | text | `Retail`, `F&B`, dll, atau `Unknown` |

#### `dim_channel`
| Kolom | Tipe | Keterangan |
|---|---|---|
| channel_id | bigint | PK (0 = Unknown) |
| nama_channel | text | `ATM`, `BI_FAST`, `QRIS`, `ATM_LINK`, `LIVIN`, `UNKNOWN` |
| jenis_channel | text | `Digital` (semua channel saat ini) atau `Unknown` |

#### `dim_wilayah`
| Kolom | Tipe | Keterangan |
|---|---|---|
| wilayah_id | bigint | PK (0 = Unknown) |
| kota | text | nama kota baku |
| provinsi | text | |
| region | text | pulau/region (Jawa, Sumatera, dll) |

#### `fact_transaksi`
| Kolom | Tipe | Keterangan |
|---|---|---|
| fact_id | bigint | PK, surrogate, berurutan |
| waktu_id | bigint | FK → dim_waktu |
| nasabah_id | bigint | FK → dim_nasabah |
| channel_id | bigint | FK → dim_channel |
| wilayah_id | bigint | FK → dim_wilayah |
| merchant_id | bigint | FK → dim_merchant |
| nominal_transaksi | bigint | nilai transaksi (Rupiah) |
| biaya_admin | double precision | biaya admin transaksi |
| trx_id | varchar | (kolom legacy, tidak diisi oleh ETL saat ini) |

### 6.3 `mvw_dashboard_transaksi` (Materialized View)

Hasil JOIN `fact_transaksi` dengan semua dimensi, satu baris = satu transaksi:

```
fact_id, tanggal, bulan, tahun, nama_lengkap, segmen_nasabah, jenis_kelamin,
nama_channel, kota, provinsi, nama_merchant, kategori_merchant,
nominal_transaksi, biaya_admin
```

Dibuat ulang (`DROP` + `CREATE`) setiap kali pipeline ETL (`main.py`) selesai
jalan — dipakai oleh **Looker Studio** untuk query langsung tanpa JOIN.

---

## 7. Tahap 3 — OLAP Cube (Atoti)

### 7.1 Kenapa Pakai Atoti?

Menyambungkan BI tool langsung ke Star Schema relasional berarti tiap query
harus JOIN ulang 6 tabel. Atoti membangun **cube in-memory**: data di-load
sekali dari PostgreSQL, JOIN & agregasi (SUM/COUNT/AVG) dilakukan di memori,
sehingga query OLAP (slice/dice/drill-down/roll-up/pivot) jadi cepat tanpa
bolak-balik ke Postgres.

### 7.2 Proses `build_cube()`

1. **Load** seluruh tabel Star Schema dari PostgreSQL via `pd.read_sql`.
   - Kolom `NUMERIC` (Decimal) → `float`
   - Kolom `DATE`/`tanggal` → `datetime64`
2. **`session.read_pandas(...)`** untuk tiap tabel, dengan:
   - `keys=[...]` → primary key tiap tabel (dipakai untuk JOIN)
   - `default_values={...}` → nilai default untuk kolom yang dipakai sebagai
     level hierarchy (syarat teknis Atoti agar kolom non-nullable)
3. **JOIN** — replikasi relasi star schema:
   ```python
   fact.join(dim_waktu,    fact["waktu_id"]    == dim_waktu["waktu_id"])
   fact.join(dim_nasabah,  fact["nasabah_id"]  == dim_nasabah["nasabah_id"])
   fact.join(dim_channel,  fact["channel_id"]  == dim_channel["channel_id"])
   fact.join(dim_wilayah,  fact["wilayah_id"]  == dim_wilayah["wilayah_id"])
   fact.join(dim_merchant, fact["merchant_id"] == dim_merchant["merchant_id"])
   ```
4. **`session.create_cube(fact, "CUBE_TRANSAKSI_MANDIRI", mode="manual")`**
   — mode manual supaya hierarchy/measure dibuat eksplisit (bukan auto-generate
   dari semua kolom).

### 7.3 Hierarchies (untuk slice/dice/drill-down/roll-up)

| Hierarchy | Level (urut umum → rinci) | Kegunaan |
|---|---|---|
| `Waktu` | tahun → quarter → bulan → tanggal | Time-series analytics |
| `Hari Transaksi` | hari (Senin–Minggu, urut kronologis) | Peak transaction day |
| `Nasabah` | segmen_nasabah → jenis_kelamin → nama_lengkap | Customer segmentation |
| `Channel` | jenis_channel → nama_channel | Digital channel analytics |
| `Nama Channel` | nama_channel (flat, 1 level) | Label bersih untuk chart channel |
| `Wilayah` | region → provinsi → kota | Geographic analytics |
| `Merchant` | kategori → nama_merchant | Merchant ecosystem analytics |

### 7.4 Measures

| Measure | Formula |
|---|---|
| `Total Volume Transaksi` | `SUM(nominal_transaksi)` |
| `Total Biaya Admin` | `SUM(biaya_admin)` |
| `Jumlah Transaksi` | `COUNT_DISTINCT(fact_id)` |
| `Rata-rata Nominal Transaksi` | `Total Volume Transaksi / Jumlah Transaksi` |

### 7.5 Operasi OLAP — Konsep & Contoh Konkret di Proyek Ini

Cube `CUBE_TRANSAKSI_MANDIRI` mendukung 5 operasi OLAP klasik. Berikut
penjelasan tiap operasi **+ contoh `cube.query()`** (lihat
`analytics/cube.py` / `dashboard/backend/cube_service.py`) **+ di mana
operasi itu muncul di dashboard**.

#### a) Slice — "mengiris" cube pada satu nilai dimensi

Memotong cube pada **satu** nilai dari **satu** dimensi, sehingga yang
tersisa adalah sub-cube dengan dimensi yang sama tapi data lebih sempit.

```python
# Contoh: total transaksi HANYA untuk tahun 2026
cube.query(
    m["Total Volume Transaksi"], m["Jumlah Transaksi"],
    filter=l["Waktu", "tahun"] == 2026,
)
```

- **Di dashboard**: memilih **satu** nilai pada dropdown filter (mis. Tahun
  = `2026`, atau Kota = `Bandung`). Diimplementasikan di
  `cube_service.build_filter()` — tiap filter yang diisi ditambahkan sebagai
  kondisi `l[level].isin(*values)`.

#### b) Dice — "memotong dadu" pada beberapa dimensi sekaligus

Memotong cube dengan **beberapa kondisi** pada **beberapa dimensi**
sekaligus → menghasilkan sub-cube yang lebih kecil tapi tetap
multidimensional.

```python
# Contoh: transaksi tahun 2026/2027, channel QRIS/BI_FAST,
# di kota Bandung/Surabaya saja
cube.query(
    m["Total Volume Transaksi"], m["Jumlah Transaksi"],
    filter=(
        l["Waktu", "tahun"].isin(2026, 2027)
        & l["Channel", "nama_channel"].isin("QRIS", "BI_FAST")
        & l["Wilayah", "kota"].isin("Bandung", "Surabaya")
    ),
)
```

- **Di dashboard**: ini persis cara kerja **FilterBar** — user mengisi
  banyak filter sekaligus (Tahun + Channel + Segmen + Kota + rentang
  tanggal, dst). Semua kondisi digabung dengan `&` di `build_filter()` dan
  dikirim sebagai satu `filter=` ke `cube.query()`. Semua endpoint chart
  (`/api/kpi`, `/api/monthly-trend`, dll) menerapkan dice yang sama secara
  konsisten — sehingga seluruh dashboard "ter-filter" bersamaan.

#### c) Roll-up (Consolidation) — naik ke level agregasi lebih umum

Mengelompokkan data ke level hierarchy yang **lebih tinggi/umum**, measure
otomatis di-agregasi ulang (SUM/COUNT) dari semua anggota di bawahnya.

```python
# Roll-up pada hierarchy Waktu: tahun -> quarter -> bulan -> tanggal
# Level paling atas (tahun) = paling "rolled up"
cube.query(m["Total Volume Transaksi"], levels=[l["Waktu", "tahun"]])
#   2026 -> total semua transaksi sepanjang tahun 2026

cube.query(m["Total Volume Transaksi"], levels=[l["Wilayah", "region"]])
#   "Jawa" -> total semua transaksi dari semua kota di Jawa
```

- **Di dashboard**: `MonthlyTrendChart` secara default menampilkan data
  **per bulan** (`get_monthly_trend()` query level `(Waktu, tahun)` +
  `(Waktu, bulan)`) — ini adalah roll-up dari level harian (`tanggal`) ke
  level bulanan. Demikian juga `CityRankingChart` (roll-up ke level kota,
  bukan per transaksi individual) dan `MerchantCategoryChart` (roll-up ke
  level kategori, bukan per merchant).

#### d) Drill-down — turun ke level lebih rinci

Kebalikan dari roll-up: dari level agregat **turun** ke level yang lebih
detail dalam hierarchy yang sama.

```python
# Drill-down pada hierarchy Waktu: dari bulanan -> harian
cube.query(
    m["Total Volume Transaksi"], m["Jumlah Transaksi"],
    levels=[l["Waktu", "tanggal"]],
    filter=(l["Waktu", "tahun"] == 2026) & (l["Waktu", "bulan"] == "April"),
)
# -> menampilkan total volume PER TANGGAL selama bulan April 2026
```

- **Di dashboard**: ini adalah fitur **drill-down interaktif** pada
  `MonthlyTrendChart` (`get_monthly_trend()` di `cube_service.py`):
  - **Default** (tidak ada filter tahun+bulan spesifik) → tampil **per
    bulan** (roll-up).
  - **Begitu user memilih TEPAT 1 Tahun DAN 1 Bulan** di FilterBar →
    backend otomatis mendeteksi (`len(tahun_list)==1 and
    len(bulan_list)==1`) dan **drill down** ke level `(Waktu, tanggal)` —
    chart yang sama berubah dari "tren per bulan dalam 1 tahun" menjadi
    "tren per hari dalam 1 bulan".
  - Hierarchy lain juga mendukung drill-down serupa kalau dipakai sebagai
    `levels` lebih dalam, misalnya `Wilayah` (region → provinsi → kota),
    `Merchant` (kategori → nama_merchant — dipakai `TopMerchantsTable`),
    dan `Nasabah` (segmen_nasabah → jenis_kelamin → nama_lengkap).

#### e) Pivot (Rotate) — menyusun ulang baris/kolom jadi matriks

Mengambil 2 dimensi sekaligus sebagai `levels`, lalu hasilnya
"diputar"/dipivot menjadi matriks 2D (baris = dimensi A, kolom = dimensi B).

```python
# Query 2 dimensi: kota x channel
df = cube.query(
    m["Jumlah Transaksi"],
    levels=[l["Wilayah", "kota"], l["Nama Channel", "nama_channel"]],
    mode="raw",
)

# Pivot jadi matriks: baris = kota, kolom = channel
pivot = df.pivot_table(
    index="kota", columns="nama_channel",
    values="Jumlah Transaksi", aggfunc="sum", fill_value=0,
)
```

- **Di dashboard**:
  - **`ChannelByRegionChart`** (`/api/channel-by-region`) — pivot **Kota x
    Channel** → stacked bar chart (tiap kota = 1 bar, tiap channel = 1
    segmen warna).
  - **`HeatmapChart`** (`/api/heatmap`) — pivot **Bulan x Hari** → heatmap
    (warna sel = jumlah transaksi pada kombinasi bulan+hari tsb), berguna
    untuk melihat pola "hari apa di bulan apa transaksi paling ramai".

### 7.6 Cara Menjalankan Cube Mandiri (Eksplorasi)

```bash
source .venv_atoti/bin/activate
export ATOTI_HIDE_EULA_MESSAGE=True
python -m analytics.cube
```

Akan mencetak URL Atoti Web App untuk eksplorasi pivot table interaktif
secara drag-and-drop di browser, plus contoh query (`run_sample_queries`)
untuk masing-masing analisis (KPI, channel, segmentasi nasabah, merchant,
geografis, tren bulanan, peak day, channel x kota).

Di Atoti Web App, operasi slice/dice/roll-up/drill-down/pivot bisa dilakukan
**secara visual** dengan drag-and-drop level/measure ke baris/kolom/filter
pivot table — sama persis dengan operasi yang dijalankan secara terprogram
oleh `cube_service.py` untuk dashboard.

---

## 8. Tahap 4 — Dashboard (Backend + Frontend)

### 8.1 Backend — FastAPI (`dashboard/backend/`)

Jalankan:
```bash
cd dashboard/backend
source ../../.venv_atoti/bin/activate
export ATOTI_HIDE_EULA_MESSAGE=True
uvicorn main:app --port 8000
```

#### `cube_service.py`
- **Singleton cube**: `get_cube()` — bangun cube sekali (lazy), simpan di
  `_session` / `_cube` global.
- **`refresh_cube()`** — tutup session lama, panggil `build_cube()` ulang
  (dipakai endpoint refresh, lihat di bawah).
- **`build_filter(cube, params)`** — terjemahkan query params dashboard
  (tahun, quarter, bulan, channel, segmen, kategori, provinsi, kota,
  start_date/end_date, include_unknown) jadi kondisi filter Atoti
  (`isin()`, `>=`, `<=`, dikombinasikan dengan `&`). Inilah implementasi
  **dice** (lihat 7.5b).
  - Default: baris **"Unknown"** (id=0 / placeholder) **disembunyikan**
    kecuali `include_unknown=true`.
- Fungsi `get_*` (satu per chart) — query cube dengan level & measure
  tertentu, format hasil jadi JSON siap pakai frontend.

#### Endpoint API (`main.py`) & Pemetaan ke Operasi OLAP

| Endpoint | Fungsi | Operasi OLAP | Level Cube | Measure |
|---|---|---|---|---|
| `GET /api/filters/options` | opsi dropdown filter (tahun, quarter, bulan, channel, segmen, kategori, provinsi, kota, min/max tanggal) | roll-up (distinct values per level) | berbagai level (tahun, quarter, bulan, dst) | `Jumlah Transaksi` |
| `POST /api/cube/refresh` | rebuild cube dari data terbaru di DB (dipanggil setelah ETL baru di-load) | - | - | - |
| `GET /api/kpi` | 4 KPI utama + trend MoM (jika filter tahun+bulan = 1 nilai) | slice/dice (grand total, tanpa level) + roll-up perbandingan bulan sebelumnya | (tanpa level — grand total) | `Total Volume Transaksi`, `Jumlah Transaksi`, `Total Biaya Admin`, `Rata-rata Nominal Transaksi` |
| `GET /api/monthly-trend` | tren transaksi per bulan, **drill-down** ke per hari jika 1 tahun+1 bulan dipilih | roll-up (default, per bulan) / **drill-down** (per hari) | `(Waktu, tahun)`+`(Waktu, bulan)` atau `(Waktu, tanggal)` | `Total Volume Transaksi`, `Jumlah Transaksi` |
| `GET /api/channel-distribution` | distribusi volume/transaksi per channel (donut) | roll-up per channel | `(Nama Channel, nama_channel)` | `Total Volume Transaksi`, `Jumlah Transaksi` |
| `GET /api/customer-segment` | distribusi per segmen nasabah (donut) | roll-up per segmen | `(Nasabah, segmen_nasabah)` | `Total Volume Transaksi`, `Jumlah Transaksi` |
| `GET /api/merchant-category` | ranking kategori merchant (bar) | roll-up per kategori | `(Merchant, kategori)` | `Total Volume Transaksi`, `Jumlah Transaksi` |
| `GET /api/top-merchants` | top N merchant by volume (tabel) | **drill-down** ke level merchant individual + ranking | `(Merchant, kategori)`+`(Merchant, nama_merchant)` | `Total Volume Transaksi`, `Jumlah Transaksi` |
| `GET /api/geographic` | data peta (kota + lat/lon + volume/jumlah) | roll-up per kota (+ provinsi) | `(Wilayah, provinsi)`+`(Wilayah, kota)` | `Total Volume Transaksi`, `Jumlah Transaksi` |
| `GET /api/city-ranking` | ranking kota by volume (bar) | roll-up per kota | `(Wilayah, kota)` | `Total Volume Transaksi`, `Jumlah Transaksi` |
| `GET /api/gender-distribution` | distribusi per jenis kelamin (donut) | roll-up per gender (+ re-aggregate manual via `groupby`) | `(Nasabah, jenis_kelamin)` | `Total Volume Transaksi`, `Jumlah Transaksi` |
| `GET /api/channel-by-region` | channel usage per kota (stacked bar) | **pivot** Kota x Channel | `(Wilayah, kota)` x `(Nama Channel, nama_channel)` | `Jumlah Transaksi` |
| `GET /api/daily-transaction` | analisis per hari (Senin–Minggu) | roll-up per hari | `(Hari Transaksi, hari)` | `Total Volume Transaksi`, `Jumlah Transaksi` |
| `GET /api/heatmap` | heatmap bulan x hari | **pivot** Bulan x Hari | `(Waktu, bulan)` x `(Hari Transaksi, hari)` | `Jumlah Transaksi` |
| `POST /api/etl/run?mode=full\|incremental` | mulai **simulasi** ETL Monitor | - | - | - |
| `GET /api/etl/status` | status simulasi ETL saat ini | - | - | - |
| `GET /api/etl/stream` | SSE stream status simulasi ETL real-time | - | - | - |

> Setiap endpoint chart di atas SELALU menerapkan **dice** dari
> `build_filter()` terlebih dahulu (sesuai filter aktif di FilterBar),
> baru kemudian melakukan operasi roll-up/drill-down/pivot sesuai
> kolom "Operasi OLAP". Jadi misalnya `ChannelByRegionChart` adalah
> **dice (filter aktif) + pivot (kota x channel)** secara bersamaan.

> Cube dibangun otomatis sekali saat backend startup (`_warm_up_cube`).
> Karena cube adalah **snapshot in-memory**, setelah ETL baru di-load ke DB,
> klik tombol **"Refresh Data"** di dashboard (atau panggil
> `POST /api/cube/refresh`) supaya dashboard menampilkan data terbaru.

### 8.2 Frontend — React + Vite (`dashboard/frontend/`)

Jalankan:
```bash
cd dashboard/frontend
npm run dev
```

#### Struktur Penting
- **`api.js`** — axios client ke backend (`http://127.0.0.1:8000/api`),
  serialisasi array filter sebagai repeated query param.
- **`context/FilterContext.jsx`** — state filter global (tahun, quarter,
  bulan, channel, segmen, kategori, provinsi, kota, rentang tanggal,
  `include_unknown`), plus `refreshAll()` (panggil `/cube/refresh` lalu
  reload opsi filter & trigger semua chart fetch ulang via `refreshKey`).
- **`hooks/useCubeQuery.js`** — hook generik: panggil fungsi `getXxx(params)`
  dari `api.js`, re-fetch otomatis saat `filters` atau `refreshKey` berubah.
- **`components/FilterBar.jsx`** — UI filter (Tahun, Quarter, Bulan, rentang
  tanggal, Channel, Segmen, Kategori, Provinsi, Kota, checkbox "Tampilkan
  data Unknown"), tombol **Refresh Data** & **Reset Filter**. Inilah panel
  kontrol untuk operasi **slice** (1 nilai filter) dan **dice** (banyak
  filter sekaligus).
- **`components/charts/*`** — 12 komponen chart/visualisasi (line, donut,
  bar, stacked bar, heatmap, peta, tabel top merchant), masing-masing pakai
  `useCubeQuery` ke endpoint terkait (lihat tabel pemetaan di 8.1).
- **`pages/DashboardPage.jsx`** — halaman utama, wrap semua dalam
  `<FilterProvider>`.
- **`pages/EtlMonitorPage.jsx`** + **`components/etl/*`** — halaman
  **ETL Monitor (Simulasi)** (lihat bagian 9).

### 8.3 Daftar Lengkap Visualisasi di Dashboard

| # | Komponen | Tipe Chart | Deskripsi |
|---|---|---|---|
| 1 | `KpiCards` | 4 kartu angka | Total Volume Transaksi, Total Frekuensi Transaksi, Total Biaya Admin (Revenue), Rata-rata Nominal Transaksi — masing-masing dengan indikator tren MoM (Month-over-Month) jika filter 1 tahun + 1 bulan dipilih |
| 2 | `MonthlyTrendChart` | Line chart | Tren volume & jumlah transaksi per bulan (roll-up); drill-down ke per hari saat 1 bulan dipilih |
| 3 | `ChannelDistributionChart` | Donut chart | Distribusi volume transaksi per channel (ATM, BI_FAST, QRIS, ATM_LINK, LIVIN) |
| 4 | `CustomerSegmentChart` | Donut chart | Kontribusi volume transaksi per segmen nasabah (Reguler, Prioritas, Private) |
| 5 | `GenderDistributionChart` | Donut chart | Distribusi volume transaksi per jenis kelamin nasabah |
| 6 | `MerchantCategoryChart` | Bar chart | Ranking kategori merchant by volume transaksi |
| 7 | `TopMerchantsTable` | Tabel sortable | Top-N merchant individual by volume, dengan kategori & frekuensi |
| 8 | `GeographicMap` | Peta interaktif (Leaflet) | Sebaran transaksi per kota (ukuran lingkaran ~ volume) |
| 9 | `CityRankingChart` | Bar chart horizontal | Ranking kota by volume transaksi |
| 10 | `ChannelByRegionChart` | Stacked bar chart | Penggunaan tiap channel di tiap kota (pivot kota x channel) |
| 11 | `DailyTransactionChart` | Bar chart | Jumlah & volume transaksi per hari (Senin–Minggu) — analisis "peak day" |
| 12 | `HeatmapChart` | Heatmap | Intensitas jumlah transaksi per kombinasi bulan x hari |

---

## 9. ETL Monitor — Simulasi Visual Pipeline

`dashboard/backend/etl_runner.py` **TIDAK menjalankan `main.py` /
ETL sungguhan** (tidak ada koneksi DB, tidak ada TRUNCATE/INSERT). Modul ini
murni **mensimulasikan** alur pipeline secara visual untuk tujuan edukasi:

- `FULL_STEPS` / `INCREMENTAL_STEPS` — daftar tahapan pipeline (sama persis
  dengan urutan nyata di `main.py` + `etl/*.py`), dikelompokkan per
  **group**: Persiapan, Dimensi, Fakta, Finalisasi.
- `_run_simulation(mode)` — jalan di thread terpisah, tiap step:
  1. status → `running`
  2. tampilkan beberapa baris **log tiruan** (`SIM_LOGS_FULL` /
     `SIM_LOGS_INCREMENTAL`) yang meniru gaya output asli `main.py`
  3. status → `success`
  4. jeda acak antar step (terasa seperti proses berjalan)
- Frontend (`EtlMonitorPage.jsx`) menampilkan progres step-by-step
  (`EtlPipeline.jsx`) + log console (`EtlLogConsole.jsx`) via SSE
  (`GET /api/etl/stream`).

Gunakan halaman ini untuk **menjelaskan alur ETL ke orang lain** secara
visual & interaktif, tanpa risiko menyentuh data produksi.

---

## 10. Tools Pendukung

| Tool | Fungsi | Cara pakai |
|---|---|---|
| `tools/generate_dirty_data.py` | Generate 20 batch data dummy "kotor" lanjutan untuk simulasi incremental load | `python3 tools/generate_dirty_data.py [--batches N] [--seed S] ...` |
| `tools/export_csv.py` | Export seluruh tabel Star Schema dari PostgreSQL ke CSV (`output_csv/`) — untuk backup/inspeksi | `python3 tools/export_csv.py` |
| `analytics/cube.py` | Build & eksplorasi OLAP Cube secara mandiri (Atoti Web App) | `python -m analytics.cube` |

---

## 11. Konfigurasi (`config.py` & `.env`)

```python
# config.py
load_dotenv()
DB_URL = os.environ["DB_URL"]          # koneksi PostgreSQL (Aiven Cloud)
DATA_DIR = os.path.join(BASE_DIR, os.environ.get("DATA_DIR", "."))
```

`.env` (tidak di-commit, berisi kredensial) minimal berisi:

```
DB_URL=postgresql+psycopg2://<user>:<password>@<host>:<port>/<dbname>?sslmode=require
DATA_DIR=data/default_data   # atau data/generate1/batch_NN untuk incremental
```

`get_engine()` mengembalikan SQLAlchemy engine yang dipakai oleh seluruh
modul ETL, `analytics/cube.py`, dan `tools/export_csv.py`.

---

## 12. Alur End-to-End Ringkas (Cheat Sheet)

```
1. python3 tools/generate_dirty_data.py
   -> data/generate1/batch_01..batch_20/*.csv  (data dummy "kotor" lanjutan)

2. (Full Load pertama, dari data/default_data)
   DATA_DIR=data/default_data python3 main.py full
   -> truncate semua tabel
   -> isi dim_waktu, dim_nasabah, dim_merchant, dim_channel, dim_wilayah
   -> isi fact_transaksi (5000 transaksi, Jan-Apr 2026)
   -> buat mvw_dashboard_transaksi

3. (Incremental Load berurutan, dari data/generate1)
   DATA_DIR=data/generate1/batch_01 python3 main.py incremental
   DATA_DIR=data/generate1/batch_02 python3 main.py incremental
   ... dst sampai batch_20
   -> tiap batch: insert dimensi baru (natural key baru saja) +
      insert fakta baru (waktu_id > watermark) + refresh materialized view

4. Jalankan backend dashboard
   cd dashboard/backend && uvicorn main:app --port 8000
   -> cube Atoti dibangun dari Star Schema saat startup

5. Jalankan frontend dashboard
   cd dashboard/frontend && npm run dev
   -> buka browser, eksplorasi KPI/chart/peta dengan filter
   -> filter = slice/dice; MonthlyTrendChart mendukung drill-down
      (pilih 1 tahun + 1 bulan); ChannelByRegion & Heatmap = pivot

6. Setiap kali ada batch baru di-load (langkah 3), klik
   "Refresh Data" di dashboard (atau POST /api/cube/refresh)
   supaya cube & dashboard menampilkan data terbaru.

7. (Opsional) Halaman "ETL Monitor" -> simulasi visual alur pipeline
   ETL untuk presentasi/edukasi (tidak menyentuh data sungguhan).

8. (Opsional) python3 tools/export_csv.py -> backup Star Schema ke CSV
9. (Opsional) python -m analytics.cube -> eksplorasi cube via Atoti Web App
```
