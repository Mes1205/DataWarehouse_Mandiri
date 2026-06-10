# 📚 Dokumentasi Step-by-Step — DataWarehouse Mandiri

Folder ini berisi dokumentasi **end-to-end** proyek Data Warehouse Mandiri,
dipecah per tahapan supaya mudah diikuti satu per satu — cocok buat belajar
ataupun presentasi.

Urutan baca yang disarankan (ikuti urutan alur datanya):

| # | File | Isi |
|---|---|---|
| 1 | [01-generate-data.md](01-generate-data.md) | Dari mana data berasal, kenapa datanya sengaja "kotor", dan bagaimana cara generate data tambahan |
| 2 | [02-etl.md](02-etl.md) | Bagaimana data kotor dibersihkan & dimuat ke Star Schema (Full Load & Incremental Load), step by step |
| 3 | [03-olap-cube.md](03-olap-cube.md) | Bagaimana data di Star Schema diubah jadi OLAP Cube (Atoti), serta apa itu slice/dice/drill-down/roll-up/pivot dengan contoh nyata |
| 4 | [04-dashboard.md](04-dashboard.md) | Cara menjalankan & menggunakan dashboard, dan bagaimana tiap chart bekerja di balik layar |

```
┌────────────────┐   ┌──────────────┐   ┌─────────────────┐   ┌─────────────┐
│ 1. Generate Data│ → │   2. ETL     │ → │ 3. OLAP Cube     │ → │ 4. Dashboard│
│   (CSV "kotor") │   │ (bersihkan & │   │ (Atoti, in-memory│   │ (FastAPI +  │
│                 │   │  load ke DB) │   │  agregasi cepat) │   │  React)     │
└────────────────┘   └──────────────┘   └─────────────────┘   └─────────────┘
```

> 💡 Untuk referensi lengkap (tabel skema database, daftar semua file
> beserta fungsinya, dll), lihat [`../dokumentasi.md`](../dokumentasi.md) di
> root proyek. Dokumen-dokumen di folder ini fokus pada **alur step-by-step**
> dengan bahasa yang lebih santai dan mudah diikuti.
