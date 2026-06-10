# 2️⃣ ETL — Membersihkan & Memuat Data ke Star Schema

ETL = **Extract, Transform, Load**. Ini adalah jantung dari Data Warehouse:
mengambil data mentah (yang "kotor", lihat [01-generate-data.md](01-generate-data.md)),
membersihkannya, lalu memuatnya ke database dalam bentuk **Star Schema**
yang rapi dan siap dianalisis.

---

## Langkah 0 — Persiapan

### a. Pastikan environment Python siap

```bash
python3.11 -m venv .venv_atoti
source .venv_atoti/bin/activate
pip install -r requirements.txt
```

### b. Siapkan file `.env` di root proyek

```env
DB_URL=postgresql+psycopg2://<user>:<password>@<host>:<port>/<dbname>?sslmode=require
DATA_DIR=data/default_data
```

- `DB_URL` → koneksi ke database PostgreSQL (di proyek ini pakai Aiven Cloud).
- `DATA_DIR` → folder mana yang akan dibaca oleh ETL sebagai sumber data.

`config.py` akan membaca `.env` ini dan menyediakan `get_engine()` (koneksi
SQLAlchemy) yang dipakai di seluruh modul ETL.

---

## Langkah 1 — Pahami Struktur Modul ETL

```
etl/
├── common.py        # helper baca CSV (auto-deteksi separator , atau ;)
├── dimensi.py        # ETL untuk 5 tabel dimensi
├── fakta.py          # ETL untuk tabel fakta + materialized view
└── wilayah_data.py    # data referensi kota -> provinsi -> region
```

Dan `main.py` adalah **dirigen/orkestrator** yang memanggil semua fungsi di
atas secara berurutan, tergantung mode yang dipilih.

---

## Langkah 2 — Mode FULL LOAD (Memuat dari Awal)

Jalankan:

```bash
DATA_DIR=data/default_data python3 main.py full
```

Mode ini cocok untuk **pertama kali** setup database. Berikut yang terjadi
**step by step**:

### Step 2.1 — Truncate Semua Tabel

```python
truncate_semua_tabel()
```

Mengosongkan `fact_transaksi` dan ke-5 tabel dimensi (`TRUNCATE ... RESTART
IDENTITY CASCADE`) — supaya kita mulai dari kondisi bersih, tidak ada data
ganda dari proses sebelumnya.

### Step 2.2 — Transform & Load Dimensi (`run_dimensi()`)

Untuk **setiap dimensi**, dilakukan extract + transform berikut:

#### `dim_waktu`
- Dibaca **langsung** dari `dim_waktu_clean.csv` — tidak perlu dibersihkan
  (sudah rapi sejak awal).

#### `dim_nasabah` (dari `nasabah_crm.csv`)
1. **Standarisasi `jenis_kelamin`** → semua variasi (`Laki-laki`, `Pria`,
   `M`, dst) diseragamkan jadi `L` / `P`. Kalau tidak dikenali / kosong →
   `U` (Unknown gender).
2. **Parse `tanggal_lahir`** — format `dd/mm/yyyy`. Kalau formatnya invalid
   (mis. `31/02/1999`), diubah jadi `NULL` (`errors='coerce'`), bukan
   error/crash.
3. **Standarisasi `segmen_nasabah`** → `RETAIL`/`Reguler` jadi `Reguler`,
   `prio`/`Prioritas` jadi `Prioritas`, dst. Kosong → `Reguler` (default).
4. Buat **surrogate key** `nasabah_id` mulai dari 1.
5. **Tambahkan 1 baris khusus**: `nasabah_id = 0`, nama = `"Unknown"` —
   baris "jaga-jaga" untuk transaksi yang kode nasabahnya tidak ditemukan.

#### `dim_merchant` (dari `merchant_mms.csv`)
1. Kolom `kategori` yang kosong → diisi `"Unknown"`.
2. Buat surrogate key `merchant_id` mulai dari 1.
3. Tambahkan baris `merchant_id = 0` ("Unknown Merchant").

#### `dim_channel` (diekstrak dari `transaksi_raw.csv`!)
Channel **tidak** punya file master sendiri — diambil dari nilai unik kolom
`channel` di data transaksi:
1. Samakan huruf besar/kecil & penamaan: `bifast`/`BIFAST` → `BI_FAST`,
   `qris` → `QRIS`, dst.
2. Ambil daftar channel unik → jadi baris-baris `dim_channel`.
3. Buat surrogate key `channel_id` mulai dari 1.
4. Tambahkan baris `channel_id = 0` (`UNKNOWN`).

#### `dim_wilayah` (diekstrak dari `transaksi_raw.csv` + master kota)
1. Normalisasi singkatan kota (`BDG` → `Bandung`, `SBY` → `Surabaya`, dst)
   menggunakan `MAP_KOTA` di `etl/wilayah_data.py`.
2. Gabungkan dengan **daftar 16 kota master** (`ALL_KOTA`) — supaya
   `dim_wilayah` tetap lengkap walaupun belum ada transaksi di kota tsb.
3. Tambahkan info `provinsi` dan `region` (pulau) untuk tiap kota.
4. Buat surrogate key `wilayah_id` mulai dari 1.
5. Tambahkan baris `wilayah_id = 0` (`Unknown`).

➡️ Setelah semua dimensi siap, **insert semua baris** ke database.

### Step 2.3 — Transform & Load Fakta (`run_fakta()`)

Ini bagian paling banyak "pembersihan"-nya, karena `transaksi_raw.csv`
adalah file paling kotor.

1. **Buang transaksi duplikat** — `drop_duplicates(subset='trx_id')`.
2. **Bersihkan `nominal`** — hapus titik ribuan, ganti koma desimal jadi
   titik, ubah jadi angka. Buang baris dengan **nominal negatif**.
3. **Bersihkan `biaya_admin`** — ubah jadi angka, kosong → `0`.
4. **Buat `waktu_id`** dari `tgl_transaksi` (format `YYYYMMDD`). Kalau
   tanggalnya invalid/kosong → baris **dibuang** (tidak bisa masuk fakta
   tanpa tanggal yang valid).
5. **Normalisasi `channel`** dan **`kota`** (sama seperti saat membuat
   dimensi).
6. **Lookup / JOIN ke surrogate key**:
   - `nasabah_code` → `nasabah_id`
   - `merchant_code` → `merchant_id`
   - `channel` (sudah dinormalisasi) → `channel_id`
   - `kota` (sudah dinormalisasi) → `wilayah_id`
   - Kalau salah satu kode **tidak ditemukan** di dimensi (mis. kosong di
     sumber) → otomatis diarahkan ke baris **"Unknown" (id = 0)** di
     dimensi terkait. Inilah kenapa setiap dimensi WAJIB punya baris id=0!
7. **Validasi**: pastikan `waktu_id` benar-benar ada di `dim_waktu`. Kalau
   tidak, baris dibuang (dengan pesan warning).
8. **Buat `fact_id`** berurutan mulai dari 1.
9. **Insert** semua baris ke `fact_transaksi`.

### Step 2.4 — Buat Materialized View (`create_materialized_view()`)

```sql
DROP MATERIALIZED VIEW IF EXISTS mvw_dashboard_transaksi;
CREATE MATERIALIZED VIEW mvw_dashboard_transaksi AS
SELECT ... -- JOIN fact_transaksi dengan semua dimensi
```

Hasilnya: 1 tabel "flat" (datar) berisi semua atribut transaksi yang sudah
ber-label (nama nasabah, nama channel, nama kota, dst) — siap dipakai
langsung oleh tools BI seperti **Looker Studio** tanpa perlu JOIN lagi.

---

## Langkah 3 — Mode INCREMENTAL LOAD (Memuat Data Baru Saja)

Setelah Full Load berhasil, kita bisa mensimulasikan "hari berikutnya"
dengan memuat batch data baru:

```bash
DATA_DIR=data/generate1/batch_01 python3 main.py incremental
DATA_DIR=data/generate1/batch_02 python3 main.py incremental
# ... lanjut sampai batch_20
```

### Apa bedanya dengan Full Load?

| | Full Load | Incremental Load |
|---|---|---|
| Truncate tabel? | ✅ Ya | ❌ Tidak |
| Dimensi | Insert semua | Insert **hanya baris baru** |
| Fakta | Insert semua | Insert **hanya transaksi baru** |

### Step 3.1 — Dimensi Incremental (`run_dimensi_incremental()`)

Untuk tiap dimensi, dilakukan transform yang **sama persis** seperti Full
Load, tapi sebelum insert, dicek dulu:

1. Ambil semua **natural key** yang sudah ada di database (mis. semua
   `nasabah_code` yang sudah tersimpan).
2. Filter data baru → hanya simpan baris yang natural key-nya **belum ada**
   di database.
3. Surrogate key (`nasabah_id`, dst) untuk baris baru **melanjutkan** dari
   nilai maksimum yang sudah ada (`MAX(id) + 1`, `MAX(id) + 2`, dst).
4. Insert hanya baris-baris baru tsb.

Pemetaan natural key per tabel:

| Tabel | Surrogate Key | Natural Key (pembanding) |
|---|---|---|
| dim_waktu | waktu_id | waktu_id |
| dim_nasabah | nasabah_id | nasabah_code |
| dim_merchant | merchant_id | merchant_code |
| dim_channel | channel_id | nama_channel |
| dim_wilayah | wilayah_id | kota |

> Karena prosesnya mengecek "sudah ada atau belum", proses ini **aman
> dijalankan berkali-kali** (idempotent) — kalau dijalankan ulang pada batch
> yang sama, tidak akan terjadi duplikat data.

### Step 3.2 — Fakta Incremental (`run_fakta_incremental()`)

1. Transform data sama seperti Full Load (bersihkan nominal, normalisasi
   channel/kota, lookup surrogate key, dst).
2. Cek **watermark**: ambil `MAX(waktu_id)` dan `MAX(fact_id)` yang sudah
   ada di `fact_transaksi`.
3. Filter → hanya simpan baris dengan `waktu_id` **lebih besar** dari
   watermark.
4. `fact_id` baris baru melanjutkan dari `MAX(fact_id) + 1`.
5. Kalau tidak ada baris baru → tampilkan pesan `"Tidak ada transaksi baru"`
   dan selesai (tidak error).

> ⚠️ **Kenapa tanggal antar batch harus berurutan?** (lihat
> [01-generate-data.md](01-generate-data.md) Langkah 3) — karena watermark
> berbasis tanggal. Kalau batch baru punya transaksi dengan tanggal **lebih
> lama** dari watermark, transaksi tsb **tidak akan ter-load**.

### Step 3.3 — Refresh Materialized View

Sama seperti Full Load — `mvw_dashboard_transaksi` di-drop & dibuat ulang
supaya berisi data terbaru.

---

## Langkah 4 — Verifikasi Hasil

Cek jumlah baris di tiap tabel, contoh dengan `psql` atau tool DB favorit:

```sql
SELECT COUNT(*) FROM fact_transaksi;
SELECT COUNT(*) FROM dim_nasabah;
SELECT * FROM dim_nasabah WHERE nasabah_id = 0;   -- baris "Unknown" harus ada
```

Atau langsung lanjut ke tahap berikutnya — **OLAP Cube** akan otomatis
membaca tabel-tabel ini dan mencetak jumlah barisnya saat di-build.

---

## Ringkasan Tahap 2

```
✅ Full Load      -> truncate + transform + load semua dimensi & fakta + buat MVW
✅ Incremental    -> transform + insert HANYA baris baru (cek natural key & watermark)
✅ Hasil akhir    -> Star Schema (1 fakta + 5 dimensi) + Materialized View di PostgreSQL
```

Lanjut ke **[03-olap-cube.md](03-olap-cube.md)** untuk melihat bagaimana
data di Star Schema ini diubah menjadi OLAP Cube yang bisa di-*slice*,
*dice*, *drill-down*, *roll-up*, dan *pivot*.
