# 3️⃣ OLAP Cube — Mengubah Star Schema Menjadi "Cube" Analitik

Setelah data rapi di Star Schema (PostgreSQL), kita perlu cara untuk
**menganalisisnya dengan cepat** — misalnya "total transaksi per bulan per
channel", "ranking kota", dst — tanpa menulis JOIN SQL berulang-ulang.

Di sinilah **OLAP Cube** berperan, menggunakan library **[Atoti](https://www.atoti.io/)**.

---

## Langkah 1 — Apa Itu OLAP Cube? (Analogi Sederhana)

Bayangkan **kubus Rubik** raksasa, di mana:

- Setiap **sisi/sumbu** kubus = 1 **dimensi** (Waktu, Wilayah, Channel,
  Nasabah, Merchant).
- Setiap **kotak kecil** di dalam kubus = kombinasi nilai dari semua sumbu
  (mis. "Bandung, April 2026, QRIS, Reguler, Kategori Retail").
- Isi tiap kotak = **measure** (angka): total nominal transaksi, jumlah
  transaksi, dst.

Karena semua data ini **sudah dimuat ke memori (RAM)** dan sudah di-JOIN
sebelumnya, query analitik jadi **sangat cepat** — tidak perlu ke database
lagi setiap kali ada permintaan dari dashboard.

---

## Langkah 2 — Persiapan Menjalankan Cube

```bash
source .venv_atoti/bin/activate
export ATOTI_HIDE_EULA_MESSAGE=True
```

> Atoti butuh **Java 17** terinstall di sistem (karena enginenya berjalan di
> atas JVM).

Untuk eksplorasi mandiri (opsional, membuka Atoti Web App di browser):

```bash
python -m analytics.cube
```

---

## Langkah 3 — Bagaimana Cube Dibangun? (`build_cube()`)

File: `analytics/cube.py`. Berikut tahapannya:

### Step 3.1 — Load Data dari PostgreSQL ke Pandas

```python
fact_transaksi = pd.read_sql("SELECT * FROM fact_transaksi", engine)
dim_waktu      = pd.read_sql("SELECT * FROM dim_waktu", engine)
dim_nasabah    = pd.read_sql("SELECT * FROM dim_nasabah", engine)
dim_merchant   = pd.read_sql("SELECT * FROM dim_merchant", engine)
dim_channel    = pd.read_sql("SELECT * FROM dim_channel", engine)
dim_wilayah    = pd.read_sql("SELECT * FROM dim_wilayah", engine)
```

Saat dijalankan, kamu akan melihat output seperti ini di terminal — ini
membuktikan cube benar-benar membaca data **terbaru** dari database:

```
>>> Membaca tabel Star Schema dari PostgreSQL...
    fact_transaksi : 32840 baris
    dim_waktu      : 10957 baris
    dim_nasabah    : 4001 baris
    dim_channel    : 6 baris
    dim_wilayah    : 17 baris
    dim_merchant   : 401 baris
```

### Step 3.2 — Masukkan Tiap Tabel ke Atoti (`session.read_pandas`)

```python
fact = session.read_pandas(fact_transaksi, table_name="Fact_Transaksi", keys=["fact_id"])
waktu = session.read_pandas(dim_waktu, table_name="Dim_Waktu", keys=["waktu_id"])
# ... dst untuk dim_nasabah, dim_merchant, dim_channel, dim_wilayah
```

`keys=[...]` menentukan **primary key** tiap tabel — dipakai Atoti untuk
melakukan JOIN.

### Step 3.3 — JOIN Antar Tabel (Replikasi Star Schema)

```python
fact.join(waktu,    fact["waktu_id"]    == waktu["waktu_id"])
fact.join(nasabah,  fact["nasabah_id"]  == nasabah["nasabah_id"])
fact.join(channel,  fact["channel_id"]  == channel["channel_id"])
fact.join(wilayah,  fact["wilayah_id"]  == wilayah["wilayah_id"])
fact.join(merchant, fact["merchant_id"] == merchant["merchant_id"])
```

Persis seperti relasi Star Schema di database — tabel fakta di tengah,
terhubung ke 5 dimensi.

### Step 3.4 — Buat Cube

```python
cube = session.create_cube(fact, "CUBE_TRANSAKSI_MANDIRI", mode="manual")
```

`mode="manual"` artinya kita **mendefinisikan sendiri** hierarchy & measure
apa saja yang dibutuhkan (bukan auto-generate dari semua kolom).

---

## Langkah 4 — Hierarchies (Sumbu-Sumbu Kubus)

**Hierarchy** = urutan level dari yang paling **umum** ke paling **rinci**.
Inilah yang memungkinkan operasi *drill-down* (turun ke detail) dan
*roll-up* (naik ke ringkasan).

| Hierarchy | Level (umum → rinci) | Contoh Kegunaan |
|---|---|---|
| `Waktu` | tahun → quarter → bulan → tanggal | Lihat tren dari tahunan sampai harian |
| `Hari Transaksi` | hari (Senin..Minggu) | Hari apa paling ramai transaksi |
| `Nasabah` | segmen_nasabah → jenis_kelamin → nama_lengkap | Segmentasi nasabah |
| `Channel` | jenis_channel → nama_channel | Analisis channel digital |
| `Nama Channel` | nama_channel (1 level saja) | Label bersih untuk chart |
| `Wilayah` | region → provinsi → kota | Analisis geografis |
| `Merchant` | kategori → nama_merchant | Analisis ekosistem merchant |

**Contoh konkret hierarchy `Waktu`:**

```
2026 (tahun)
 └── Q2 (quarter)
      └── April (bulan)
           └── 2026-04-15 (tanggal)
```

---

## Langkah 5 — Measures (Angka yang Dihitung)

| Measure | Cara hitung |
|---|---|
| `Total Volume Transaksi` | `SUM(nominal_transaksi)` |
| `Total Biaya Admin` | `SUM(biaya_admin)` |
| `Jumlah Transaksi` | `COUNT_DISTINCT(fact_id)` |
| `Rata-rata Nominal Transaksi` | `Total Volume Transaksi ÷ Jumlah Transaksi` |

---

## Langkah 6 — 5 Operasi OLAP Inti (+ Contoh Nyata)

Inilah **inti** dari analisis OLAP. Mari kita bahas satu-satu, dengan contoh
yang benar-benar dipakai di proyek ini.

### a) 🔪 Slice — "Mengiris" jadi 1 Bagian

> Memotong cube pada **satu nilai** dari **satu dimensi**.

**Contoh**: "Tampilkan total transaksi **HANYA** untuk tahun 2026"

```python
cube.query(
    m["Total Volume Transaksi"], m["Jumlah Transaksi"],
    filter=l["Waktu", "tahun"] == 2026,
)
```

**Di dashboard**: ketika kamu memilih **satu** nilai di dropdown filter
(mis. Tahun = `2026`, atau Kota = `Bandung`).

---

### b) 🎲 Dice — "Memotong Dadu" dari Beberapa Sisi Sekaligus

> Memotong cube dengan **beberapa kondisi** pada **beberapa dimensi**
> sekaligus.

**Contoh**: "Tampilkan transaksi tahun 2026 ATAU 2027, channel QRIS ATAU
BI_FAST, di kota Bandung ATAU Surabaya"

```python
cube.query(
    m["Total Volume Transaksi"], m["Jumlah Transaksi"],
    filter=(
        l["Waktu", "tahun"].isin(2026, 2027)
        & l["Channel", "nama_channel"].isin("QRIS", "BI_FAST")
        & l["Wilayah", "kota"].isin("Bandung", "Surabaya")
    ),
)
```

**Di dashboard**: ini persis cara kerja **Filter Bar** — kamu bisa
mengaktifkan banyak filter sekaligus (Tahun + Channel + Kota + Segmen +
rentang tanggal), dan **semua chart** akan menyesuaikan secara bersamaan.

---

### c) 📈 Roll-up — Naik ke Level yang Lebih Umum (Ringkasan)

> Mengelompokkan data ke level yang **lebih tinggi**, angka otomatis
> dijumlahkan dari level di bawahnya.

**Contoh**: "Total transaksi **per tahun**" (bukan per hari/bulan)

```python
cube.query(m["Total Volume Transaksi"], levels=[l["Waktu", "tahun"]])
# Hasil: 2026 -> Rp xxx (jumlah dari SEMUA transaksi sepanjang 2026)
```

Contoh lain: "Total transaksi **per region**" (Jawa, Sumatera, dst) — ini
roll-up dari level kota ke level region.

**Di dashboard**: `MonthlyTrendChart` secara default menampilkan data
**per bulan** — ini roll-up dari data harian ke bulanan. Begitu juga
`CityRankingChart` (roll-up ke level kota) dan `MerchantCategoryChart`
(roll-up ke level kategori merchant).

---

### d) 🔍 Drill-Down — Turun ke Level Lebih Rinci

> Kebalikan dari roll-up: dari ringkasan, **turun** untuk melihat detail.

**Contoh**: "Saya sudah lihat total April 2026, sekarang tampilkan **per
tanggal** dalam bulan itu"

```python
cube.query(
    m["Total Volume Transaksi"], m["Jumlah Transaksi"],
    levels=[l["Waktu", "tanggal"]],
    filter=(l["Waktu", "tahun"] == 2026) & (l["Waktu", "bulan"] == "April"),
)
```

**Di dashboard**: ini adalah fitur **interaktif** di `MonthlyTrendChart`!

- **Default** (belum pilih tahun+bulan spesifik) → grafik tampil **per
  bulan** (roll-up).
- **Begitu kamu pilih TEPAT 1 Tahun DAN 1 Bulan** di Filter Bar → grafik
  otomatis **drill-down** menjadi **per tanggal/hari** dalam bulan tersebut.

Coba sendiri: pilih `Tahun = 2026` dan `Bulan = April` di dashboard, lalu
lihat `MonthlyTrendChart` berubah dari "per bulan" jadi "per hari"!

---

### e) 🔄 Pivot — Menyusun Data jadi Tabel Silang (Matriks)

> Mengambil **2 dimensi sekaligus**, lalu menyusunnya jadi matriks: baris =
> dimensi A, kolom = dimensi B.

**Contoh**: "Buat tabel: baris = Kota, kolom = Channel, isi = jumlah
transaksi"

```python
df = cube.query(
    m["Jumlah Transaksi"],
    levels=[l["Wilayah", "kota"], l["Nama Channel", "nama_channel"]],
    mode="raw",
)

pivot = df.pivot_table(
    index="kota", columns="nama_channel",
    values="Jumlah Transaksi", aggfunc="sum", fill_value=0,
)
```

Hasilnya kira-kira:

| Kota | ATM | BI_FAST | QRIS | LIVIN |
|---|---|---|---|---|
| Bandung | 120 | 340 | 980 | 210 |
| Surabaya | 95 | 410 | 875 | 180 |

**Di dashboard**:
- `ChannelByRegionChart` → pivot **Kota x Channel** → ditampilkan sebagai
  *stacked bar chart*.
- `HeatmapChart` → pivot **Bulan x Hari** → ditampilkan sebagai *heatmap*
  (warna sel = intensitas jumlah transaksi).

---

## Langkah 7 — Ringkasan: 1 Tabel untuk Semua Operasi

| Operasi | Pertanyaan Khas | Contoh di Proyek Ini |
|---|---|---|
| **Slice** | "Tampilkan **hanya** untuk X" | Filter Tahun = 2026 |
| **Dice** | "Tampilkan untuk kombinasi X, Y, Z" | Filter Tahun + Channel + Kota sekaligus |
| **Roll-up** | "Ringkas jadi level yang lebih umum" | Tren bulanan (bukan harian) |
| **Drill-down** | "Lihat detail di level bawahnya" | Tren harian dalam 1 bulan terpilih |
| **Pivot** | "Susun jadi tabel silang 2 dimensi" | Kota x Channel, Bulan x Hari |

---

## Ringkasan Tahap 3

```
✅ Cube dibangun dari 6 tabel di PostgreSQL (1 fakta + 5 dimensi)
✅ Hierarchies = sumbu kubus (Waktu, Wilayah, Channel, Nasabah, Merchant)
✅ Measures = angka yang dihitung (Volume, Jumlah, Biaya Admin, Rata-rata)
✅ 5 operasi OLAP: Slice, Dice, Roll-up, Drill-down, Pivot
```

Lanjut ke **[04-dashboard.md](04-dashboard.md)** untuk melihat bagaimana
semua operasi ini ditampilkan dalam bentuk dashboard interaktif yang bisa
diklik-klik!
