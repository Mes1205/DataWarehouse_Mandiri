# etl/wilayah_data.py
# Data referensi wilayah (kota -> provinsi -> region/pulau) yang dipakai
# bersama oleh etl/dimensi.py, etl/fakta.py, dan tools/generate_dirty_data.py.
#
# Modul ini sengaja tidak mengimpor apa pun selain stdlib supaya bisa dipakai
# oleh tools/generate_dirty_data.py (generator data dummy) tanpa butuh koneksi
# database (config.py butuh DB_URL dari .env).

# Normalisasi singkatan/variasi nama kota dari sumber data ke nama baku.
MAP_KOTA = {
    'BDG': 'Bandung',
    'Jkt Sel': 'Jakarta Selatan',
    'SBY': 'Surabaya',
}

# kota -> (provinsi, region/pulau). Minimal 15 kota dari berbagai pulau
# Indonesia supaya dimensi wilayah merepresentasikan cakupan nasional.
KOTA_INFO = {
    'Jakarta Selatan': ('DKI Jakarta', 'Jawa'),
    'Bandung':         ('Jawa Barat', 'Jawa'),
    'Surabaya':        ('Jawa Timur', 'Jawa'),
    'Semarang':        ('Jawa Tengah', 'Jawa'),
    'Yogyakarta':      ('DI Yogyakarta', 'Jawa'),
    'Medan':           ('Sumatera Utara', 'Sumatera'),
    'Palembang':       ('Sumatera Selatan', 'Sumatera'),
    'Padang':          ('Sumatera Barat', 'Sumatera'),
    'Pekanbaru':       ('Riau', 'Sumatera'),
    'Banjarmasin':     ('Kalimantan Selatan', 'Kalimantan'),
    'Balikpapan':      ('Kalimantan Timur', 'Kalimantan'),
    'Pontianak':       ('Kalimantan Barat', 'Kalimantan'),
    'Makassar':        ('Sulawesi Selatan', 'Sulawesi'),
    'Manado':          ('Sulawesi Utara', 'Sulawesi'),
    'Denpasar':        ('Bali', 'Bali & Nusa Tenggara'),
    'Jayapura':        ('Papua', 'Papua'),
}

MAP_PROV = {kota: info[0] for kota, info in KOTA_INFO.items()}
MAP_REGION = {kota: info[1] for kota, info in KOTA_INFO.items()}

# Master list nama kota baku -- dipakai untuk pre-populate dim_wilayah supaya
# semua kota sudah terdaftar sejak awal, walau belum ada transaksinya.
ALL_KOTA = list(KOTA_INFO.keys())
