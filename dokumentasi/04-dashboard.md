# 4️⃣ Dashboard — Visualisasi Interaktif

Ini adalah tahap terakhir: menampilkan hasil OLAP Cube ([03-olap-cube.md](03-olap-cube.md))
dalam bentuk **dashboard web** yang interaktif — bisa difilter, diklik, dan
di-refresh kapan saja.

Dashboard terdiri dari 2 bagian:

- **Backend** (`dashboard/backend/`) — FastAPI, menjembatani antara cube
  Atoti dan frontend.
- **Frontend** (`dashboard/frontend/`) — React + Vite, menampilkan UI.

---

## Langkah 1 — Menjalankan Dashboard

### Cara termudah (1 perintah)

```bash
./run_dashboard.sh
```

Script ini akan:
1. Menjalankan backend (membangun cube + serve API di `http://127.0.0.1:8000`)
2. Menunggu sampai cube selesai dibangun
3. Install dependency frontend (kalau belum) lalu menjalankan frontend di
   `http://localhost:5173`

Buka browser ke **http://localhost:5173**.

### Cara manual (2 terminal terpisah)

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

> 📝 Backend **tidak** dijalankan dengan `--reload` (ada isu kompatibilitas
> di proyek ini). Jadi kalau kamu mengubah kode backend, kamu perlu
> `Ctrl+C` lalu jalankan ulang `uvicorn main:app --port 8000`.

---

## Langkah 2 — Tur Halaman Dashboard

Saat pertama dibuka, kamu akan melihat:

### 2.1 — Filter Bar (paling atas)

Panel filter global yang memengaruhi **SEMUA** chart sekaligus. Ini adalah
implementasi nyata dari operasi **Slice** & **Dice** yang dibahas di
[03-olap-cube.md](03-olap-cube.md):

| Filter | Contoh |
|---|---|
| Tahun, Quarter, Bulan | 2026, Q2, April |
| Rentang tanggal (dari–sampai) | 2026-04-01 s/d 2026-04-30 |
| Channel | QRIS, BI_FAST, dst (bisa pilih lebih dari satu) |
| Segmen Nasabah | Reguler, Prioritas, Private |
| Kategori Merchant | Retail, F&B, dst |
| Provinsi & Kota | Jawa Barat, Bandung, dst |
| ☑️ Tampilkan data Unknown | sembunyikan/tampilkan baris fallback "Unknown" |

Tombol di kanan:
- **Refresh Data** — bangun ulang cube dari data terbaru di database (lihat
  Langkah 4).
- **Reset Filter** — kembalikan semua filter ke kondisi awal.

> 💡 **Coba ini**: pilih `Tahun = 2026` dan `Bulan = April`, lalu perhatikan
> chart "Tren Bulanan" berubah jadi tampilan **harian** (drill-down
> otomatis!).

### 2.2 — KPI Cards (4 kartu angka)

| KPI | Penjelasan |
|---|---|
| Total Volume Transaksi | Jumlah seluruh nominal transaksi (Rp) |
| Total Frekuensi Transaksi | Berapa kali transaksi terjadi |
| Total Biaya Admin (Revenue) | Total pendapatan dari biaya admin |
| Rata-rata Nominal Transaksi | Volume ÷ Frekuensi |

Kalau kamu memilih **tepat 1 Tahun + 1 Bulan**, setiap kartu juga akan
menampilkan **trend naik/turun (%)** dibanding bulan sebelumnya.

### 2.3 — Grid Chart (12 visualisasi)

| # | Chart | Bentuk | Yang Ditampilkan |
|---|---|---|---|
| 1 | Tren Bulanan | Line chart | Volume & jumlah transaksi per bulan (atau per hari jika drill-down) |
| 2 | Distribusi Channel | Donut chart | Porsi transaksi per channel (ATM, QRIS, dst) |
| 3 | Segmen Nasabah | Donut chart | Porsi transaksi per segmen (Reguler/Prioritas/Private) |
| 4 | Distribusi Gender | Donut chart | Porsi transaksi berdasarkan jenis kelamin |
| 5 | Kategori Merchant | Bar chart | Ranking kategori merchant by volume |
| 6 | Top Merchant | Tabel | Daftar merchant teratas (bisa di-sort) |
| 7 | Peta Sebaran | Peta interaktif | Sebaran transaksi per kota (ukuran lingkaran = volume) |
| 8 | Ranking Kota | Bar chart horizontal | Kota dengan volume transaksi tertinggi |
| 9 | Channel per Wilayah | Stacked bar chart | Channel apa yang populer di tiap kota (pivot) |
| 10 | Transaksi Harian | Bar chart | Hari apa (Senin-Minggu) paling ramai |
| 11 | Heatmap | Heatmap | Bulan x Hari — kombinasi mana yang paling ramai (pivot) |

---

## Langkah 3 — Apa yang Terjadi di Belakang Layar Saat Kamu Klik Filter?

```
1. Kamu ubah filter di Filter Bar (mis. pilih Tahun=2026)
        │
        ▼
2. Frontend (FilterContext.jsx) menyimpan filter baru
        │
        ▼
3. Setiap komponen chart (via hook useCubeQuery) otomatis fetch ulang
   ke endpoint masing-masing, mis: GET /api/monthly-trend?tahun=2026
        │
        ▼
4. Backend (cube_service.py) menerjemahkan filter -> query Atoti
   (ini operasi DICE: gabungan semua filter aktif)
        │
        ▼
5. Atoti cube menghitung hasil di memori (cepat!) -> backend kirim JSON
        │
        ▼
6. Chart di-render ulang dengan data baru
```

### Pemetaan Tiap Chart ke Endpoint & Operasi OLAP

| Chart | Endpoint | Operasi OLAP |
|---|---|---|
| KPI Cards | `/api/kpi` | Slice/Dice (total keseluruhan sesuai filter) |
| Tren Bulanan | `/api/monthly-trend` | Roll-up (per bulan) / **Drill-down** (per hari) |
| Distribusi Channel | `/api/channel-distribution` | Roll-up per channel |
| Segmen Nasabah | `/api/customer-segment` | Roll-up per segmen |
| Distribusi Gender | `/api/gender-distribution` | Roll-up per gender |
| Kategori Merchant | `/api/merchant-category` | Roll-up per kategori |
| Top Merchant | `/api/top-merchants` | Drill-down ke level merchant + ranking |
| Peta Sebaran | `/api/geographic` | Roll-up per kota |
| Ranking Kota | `/api/city-ranking` | Roll-up per kota |
| Channel per Wilayah | `/api/channel-by-region` | **Pivot** Kota x Channel |
| Transaksi Harian | `/api/daily-transaction` | Roll-up per hari |
| Heatmap | `/api/heatmap` | **Pivot** Bulan x Hari |

> Setiap endpoint **selalu** menerapkan filter aktif (dice) terlebih dahulu,
> baru melakukan roll-up/drill-down/pivot sesuai jenis chartnya.

---

## Langkah 4 — Refresh Data Setelah Ada ETL Baru

Cube Atoti adalah **snapshot** data di memori — dia **tidak otomatis tahu**
kalau ada data baru masuk ke database (mis. setelah kamu jalankan
`python main.py incremental` untuk batch baru).

### Cara refresh:

**Opsi 1 — Klik tombol di dashboard**
Klik **"Refresh Data"** di Filter Bar. Tombol akan menampilkan "Memuat..."
sampai selesai.

**Opsi 2 — Panggil API langsung**
```bash
curl -X POST http://127.0.0.1:8000/api/cube/refresh
```

### Apa yang terjadi saat refresh?

```python
def refresh_cube():
    # 1. Tutup session atoti yang lama
    _session.close()
    # 2. Bangun ulang cube dari data TERBARU di database
    _session, _cube = build_cube()
```

Setelah refresh selesai, frontend otomatis memuat ulang opsi filter dan
semua chart — **tanpa perlu restart backend sama sekali**.

---

## Langkah 5 — ETL Monitor (Simulasi Visual)

Selain dashboard analitik, ada juga halaman **"ETL Monitor"**
(`/etl` di frontend) yang menampilkan **visualisasi alur pipeline ETL**
secara step-by-step dengan log "live".

> ⚠️ **Penting**: halaman ini adalah **SIMULASI** untuk tujuan edukasi/demo
> — tidak benar-benar menjalankan `main.py` atau menyentuh database.

### Cara pakai:

1. Pilih mode: **Full Load** atau **Incremental**.
2. Klik **"Jalankan Simulasi"**.
3. Perhatikan setiap tahap (Persiapan → Dimensi → Fakta → Finalisasi)
   berubah status: `pending` → `running` → `success`, lengkap dengan log
   tiruan yang meniru output asli `main.py`.

Cocok dipakai untuk **menjelaskan alur ETL ke orang lain** secara visual,
tanpa risiko mengubah data sungguhan.

---

## Langkah 6 — Troubleshooting Singkat

| Masalah | Solusi |
|---|---|
| Backend gagal start, error `Attribute "app" not found` saat pakai `--reload` | Jangan pakai `--reload`. Jalankan `uvicorn main:app --port 8000` biasa. |
| Klik "Refresh Data" tapi data tidak berubah | Cek apakah ada proses backend lama yang masih jalan (`pkill -f "uvicorn main:app"`), lalu start ulang dengan kode terbaru. |
| Frontend tidak bisa konek ke backend | Pastikan backend jalan di port `8000` dan CORS sudah aktif (`main.py`). |
| Cube gagal dibangun / error koneksi DB | Cek `.env` (`DB_URL`) dan pastikan tabel Star Schema sudah terisi (jalankan ETL dulu, lihat [02-etl.md](02-etl.md)). |

---

## Ringkasan Tahap 4

```
✅ Backend (FastAPI) -> bangun cube sekali saat startup, sediakan endpoint /api/*
✅ Frontend (React)  -> Filter Bar (slice/dice) + 12 chart + KPI
✅ Refresh Data      -> rebuild cube tanpa restart backend
✅ ETL Monitor       -> simulasi visual alur pipeline (edukasi, tidak menyentuh DB)
```

🎉 **Selesai!** Kamu sudah memahami seluruh alur Data Warehouse Mandiri:
**Generate Data → ETL → OLAP Cube → Dashboard**.

Untuk referensi lebih lengkap (skema database detail, daftar semua file &
fungsinya), lihat [`../dokumentasi.md`](../dokumentasi.md).
