# 1️⃣ Generate Data — Sumber Data Mentah

Tahap paling awal dari sebuah Data Warehouse adalah **data sumber**. Di
dunia nyata, data ini biasanya datang dari sistem operasional bank seperti
CRM (data nasabah), MMS (data merchant), dan sistem transaksi (core banking,
e-channel).

Di proyek ini, semua data sumber tersebut **disimulasikan dalam bentuk file
CSV**, dan **sengaja dibuat "kotor"** — supaya proses ETL punya sesuatu yang
benar-benar perlu dibersihkan (sama seperti kondisi nyata di industri).

---

## Langkah 1 — Pahami Dataset Awal (`data/default_data/`)

Ini adalah dataset **bawaan** yang dipakai untuk **Full Load** pertama kali.
Ada 4 file:

| File | Isi | Jumlah Baris |
|---|---|---|
| `dim_waktu_clean.csv` | Kalender harian dari **2001-01-01** sampai **2030-12-31** | 10.957 |
| `nasabah_crm.csv` | Data nasabah (kode `N-10001` s/d `N-11000`) | 1.000 |
| `merchant_mms.csv` | Data merchant (kode `MCH-5001` s/d `MCH-5100`) | 100 |
| `transaksi_raw.csv` | Transaksi mentah (kode `TRX-200001` s/d `TRX-204999`), tanggal **Jan–Apr 2026** | 5.000 |

Bayangkan 4 file ini sebagai **4 sistem berbeda** yang "export" datanya ke
CSV setiap periode tertentu.

### Format kolom tiap file

```
nasabah_crm.csv   : nasabah_code;nama_lengkap;jenis_kelamin;tanggal_lahir;segmen_nasabah
merchant_mms.csv  : merchant_code;nama_merchant;kategori
transaksi_raw.csv : trx_id;tgl_transaksi;nasabah_code;channel;merchant_code;kota;nominal;biaya_admin
dim_waktu_clean.csv: waktu_id;tanggal;hari;bulan;tahun;quarter   (sudah bersih)
```

> 📌 `dim_waktu_clean.csv` **TIDAK kotor** — kalender memang biasanya sudah
> disiapkan rapi sejak awal (master data), jadi tidak perlu dibersihkan lagi.

---

## Langkah 2 — Kenapa Datanya "Kotor"? Apa Saja Jenis Kotornya?

Di dunia nyata, data dari sistem operasional jarang sekali rapi 100%. Maka
di `transaksi_raw.csv`, `nasabah_crm.csv`, dan `merchant_mms.csv`, sengaja
diselipkan beberapa "penyakit data" berikut:

| Kolom | Contoh "Kotor" | Kenapa Ini Realistis? |
|---|---|---|
| `jenis_kelamin` | `L, P, M, Laki-laki, Female, Pria, Wanita, ''` | Tiap sistem/cabang sering input dengan format beda-beda |
| `segmen_nasabah` | `Reguler, Prioritas, RETAIL, prio, Private, ''` | Penamaan segmen berubah seiring waktu / typo |
| `tanggal_lahir` | kosong, atau tanggal aneh seperti `31/02/1999` | Data lama sering tidak lengkap atau salah input |
| `kategori` (merchant) | `Retail, F&B, Food & Beverage, Health, Kesehatan, ''` | Penamaan kategori belum distandarkan |
| `channel` | `ATM, BI_FAST, BIFAST, bifast, qris, livin` | Beda huruf besar/kecil, beda penulisan |
| `kota` | nama lengkap vs singkatan: `BDG`, `Jkt Sel`, `SBY` | Operator sering pakai singkatan |
| `tgl_transaksi` | ~2% kosong, ~2% format salah (`31-13-2026`) | Input manual rawan salah |
| `nominal` | format Indonesia (`1.000.000`), kadang ada yang **negatif** | Salah ketik / refund tercatat sebagai transaksi |
| `biaya_admin` | ~5% kosong | Tidak semua channel kena biaya admin |
| `trx_id` | ~2% **duplikat** | Gangguan sistem / retry transaksi |
| `nasabah_code` / `merchant_code` / `channel` / `kota` | ~2% **kosong** | Data tidak lengkap saat dikirim antar sistem |

Semua "penyakit" ini punya solusinya masing-masing di tahap ETL (lihat
[02-etl.md](02-etl.md)) — jadi jangan khawatir, semuanya sudah ditangani! 😉

---

## Langkah 3 — Generate Data Tambahan untuk Simulasi "Hari Berikutnya"

Supaya kita bisa mensimulasikan **data warehouse yang terus bertambah**
(seperti kondisi nyata: setiap hari ada transaksi baru), proyek ini punya
script generator: `tools/generate_dirty_data.py`.

### Cara menjalankan

```bash
source .venv_atoti/bin/activate
python3 tools/generate_dirty_data.py
```

### Apa yang terjadi?

Script ini akan membuat **20 folder batch** baru di `data/generate1/`:

```
data/generate1/
├── batch_01/
│   ├── nasabah_crm.csv
│   ├── merchant_mms.csv
│   └── transaksi_raw.csv
├── batch_02/
│   └── ... (sama)
...
└── batch_20/
    └── ...
```

Setiap batch berisi data **lanjutan** dari `default_data` (kode tidak
tumpang tindih):

| Entitas | Kode lanjutan mulai dari | Jumlah per batch |
|---|---|---|
| Nasabah baru | `N-11001` dst | 1.000 |
| Merchant baru | `MCH-5101` dst | 100 |
| Transaksi baru | `TRX-205000` dst | 10.000 (+ ~2% duplikat) |

### Kenapa harus 20 batch terpisah, bukan 1 file besar?

Supaya kita bisa mensimulasikan **proses incremental load berkali-kali**
(`python main.py incremental`) — **1 batch = 1 "hari operasional baru"**.

### ⚠️ Hal penting: tanggal antar batch berurutan & tidak tumpang tindih

Tanggal transaksi di tiap batch dibuat **berurutan** (batch_01 paling awal,
batch_20 paling akhir, rentang `2026-04-12` s/d `2030-12-31`) dan **tidak
saling overlap**.

Ini penting karena di tahap ETL, proses incremental memakai **watermark**
(tanggal transaksi terbaru yang sudah ada di database). Kalau tanggal antar
batch acak/tumpang tindih, batch berikutnya bisa "dianggap tidak ada data
baru" walaupun sebenarnya ada.

---

## Langkah 4 — Selesai! Lanjut ke Tahap ETL

Setelah dataset awal (`data/default_data/`) dan dataset tambahan
(`data/generate1/batch_01..20/`) siap, kita lanjut ke tahap berikutnya:
**membersihkan & memuat data ini ke database** → lihat
**[02-etl.md](02-etl.md)**.

### Ringkasan Tahap 1

```
✅ data/default_data/        -> dipakai untuk Full Load pertama kali
✅ data/generate1/batch_01..20/ -> dipakai untuk simulasi Incremental Load
✅ Semua data sengaja "kotor" -> akan dibersihkan di tahap ETL
```
