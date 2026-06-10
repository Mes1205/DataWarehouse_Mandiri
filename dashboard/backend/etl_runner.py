# dashboard/backend/etl_runner.py
#
# Simulasi visual pipeline ETL untuk halaman "ETL Monitor" di dashboard.
#
# CATATAN: modul ini TIDAK menjalankan main.py / etl/*.py yang sesungguhnya —
# tidak ada koneksi database, tidak ada TRUNCATE, tidak ada perubahan data.
# Tujuannya murni memvisualisasikan alur & tahapan pipeline ETL nyata
# (CSV -> Star Schema -> Materialized View) secara step-by-step dengan log
# tiruan yang merepresentasikan output asli main.py, supaya mudah dipahami
# tanpa risiko menyentuh data produksi.

import random
import threading
import time

FULL_STEPS = [
    {"key": "truncate", "group": "Persiapan",
     "label": "Truncate Tabel",
     "desc": "Mengosongkan semua tabel fakta & dimensi sebelum load ulang"},

    {"key": "extract_dim", "group": "Dimensi",
     "label": "Ekstrak Data Sumber",
     "desc": "Membaca CSV dim_waktu, nasabah_crm, merchant_mms, transaksi_raw"},
    {"key": "transform_waktu", "group": "Dimensi",
     "label": "Transform Dimensi Waktu",
     "desc": "Menyiapkan kalender harian (dim_waktu)"},
    {"key": "transform_nasabah", "group": "Dimensi",
     "label": "Transform Dimensi Nasabah",
     "desc": "Standarisasi kode jenis kelamin, parsing tanggal lahir, normalisasi segmen nasabah"},
    {"key": "transform_merchant", "group": "Dimensi",
     "label": "Transform Dimensi Merchant",
     "desc": "Isi kategori kosong dengan 'Unknown', buat surrogate key merchant"},
    {"key": "transform_channel", "group": "Dimensi",
     "label": "Transform Dimensi Channel",
     "desc": "Ekstrak channel unik & benerin penamaan (BIFAST -> BI_FAST)"},
    {"key": "transform_wilayah", "group": "Dimensi",
     "label": "Transform Dimensi Wilayah",
     "desc": "Ekstrak kota unik & benerin penamaan (BDG -> Bandung, dst), tambah provinsi"},
    {"key": "load_dimensi", "group": "Dimensi",
     "label": "Load Dimensi ke Database",
     "desc": "Insert seluruh baris dimensi ke PostgreSQL"},

    {"key": "transform_fakta", "group": "Fakta",
     "label": "Ekstrak & Bersihkan Data Transaksi",
     "desc": "Hapus duplikat trx_id, bersihkan format nominal, buang baris nominal negatif/tanggal tidak valid, benerin penamaan channel & kota"},
    {"key": "validate_fakta", "group": "Fakta",
     "label": "Lookup Surrogate Key & Validasi",
     "desc": "Join ke dimensi (nasabah, merchant, channel, wilayah), validasi waktu_id ke dim_waktu"},
    {"key": "load_fakta", "group": "Fakta",
     "label": "Load Fakta ke Database",
     "desc": "Insert seluruh baris fact_transaksi ke PostgreSQL"},

    {"key": "mvw", "group": "Finalisasi",
     "label": "Build Materialized View",
     "desc": "Drop & buat ulang mvw_dashboard_transaksi untuk Looker Studio"},
]

INCREMENTAL_STEPS = [
    {"key": "extract_dim", "group": "Dimensi",
     "label": "Ekstrak Data Sumber",
     "desc": "Membaca CSV dim_waktu, nasabah_crm, merchant_mms, transaksi_raw"},
    {"key": "transform_waktu", "group": "Dimensi",
     "label": "Transform Dimensi Waktu",
     "desc": "Menyiapkan kalender harian (dim_waktu)"},
    {"key": "transform_nasabah", "group": "Dimensi",
     "label": "Transform Dimensi Nasabah",
     "desc": "Standarisasi kode jenis kelamin, parsing tanggal lahir, normalisasi segmen nasabah"},
    {"key": "transform_merchant", "group": "Dimensi",
     "label": "Transform Dimensi Merchant",
     "desc": "Isi kategori kosong dengan 'Unknown', buat surrogate key merchant"},
    {"key": "transform_channel", "group": "Dimensi",
     "label": "Transform Dimensi Channel",
     "desc": "Ekstrak channel unik & benerin penamaan (BIFAST -> BI_FAST)"},
    {"key": "transform_wilayah", "group": "Dimensi",
     "label": "Transform Dimensi Wilayah",
     "desc": "Ekstrak kota unik & benerin penamaan (BDG -> Bandung, dst), tambah provinsi"},
    {"key": "load_dimensi", "group": "Dimensi",
     "label": "Cek & Insert Data Baru (Dimensi)",
     "desc": "Bandingkan natural key dengan data di DB, insert baris dimensi yang baru saja"},

    {"key": "transform_fakta", "group": "Fakta",
     "label": "Ekstrak & Bersihkan Data Transaksi",
     "desc": "Hapus duplikat trx_id, bersihkan format nominal, buang baris nominal negatif/tanggal tidak valid, benerin penamaan channel & kota"},
    {"key": "validate_fakta", "group": "Fakta",
     "label": "Lookup Surrogate Key & Cek Watermark",
     "desc": "Join ke dimensi, validasi waktu_id, bandingkan dengan watermark waktu_id terakhir"},
    {"key": "load_fakta", "group": "Fakta",
     "label": "Cek & Insert Data Baru (Fakta)",
     "desc": "Insert hanya transaksi dengan waktu_id di atas watermark"},

    {"key": "mvw", "group": "Finalisasi",
     "label": "Build Materialized View",
     "desc": "Drop & buat ulang mvw_dashboard_transaksi untuk Looker Studio"},
]

# Log tiruan per step -- meniru gaya output asli main.py / etl/*.py supaya
# pengguna paham apa yang "biasanya" terjadi pada tahap tsb tanpa benar-benar
# menjalankan query ke database.
SIM_LOGS_FULL = {
    "truncate": [
        "Truncate tabel lama...",
        "Semua tabel berhasil dikosongkan.",
    ],
    "extract_dim": [
        ">>> Mulai ETL Dimensi (Full Load)...",
        "Kolom nasabah: ['nasabah_code', 'nama_lengkap', 'tanggal_lahir', 'jenis_kelamin', 'segmen_nasabah']",
    ],
    "transform_waktu": [
        "    dim_waktu      : 10957 baris",
    ],
    "transform_nasabah": [
        "    dim_nasabah    : 1001 baris (termasuk Unknown)",
    ],
    "transform_merchant": [
        "    dim_merchant   : 101 baris (termasuk Unknown)",
    ],
    "transform_channel": [
        "    dim_channel    : 6 baris (termasuk Unknown)",
    ],
    "transform_wilayah": [
        "    dim_wilayah    : 17 baris (termasuk Unknown)",
    ],
    "load_dimensi": [
        "    -> Insert ke database...",
        ">>> Dimensi SELESAI!",
    ],
    "transform_fakta": [
        ">>> Mulai ETL Fakta (Full Load)...",
        "    Membersihkan nominal, membuang duplikat & baris tidak valid...",
    ],
    "validate_fakta": [
        "    Lookup surrogate key ke dim_nasabah, dim_merchant, dim_channel, dim_wilayah...",
        "    Total baris fakta siap insert: 5000",
    ],
    "load_fakta": [
        "    -> Insert ke tabel fakta...",
        ">>> Fakta SELESAI!",
    ],
    "mvw": [
        ">>> Membuat Materialized View untuk Looker Studio di Aiven...",
        "✓ Materialized View berhasil dibuat di Aiven!",
    ],
}

SIM_LOGS_INCREMENTAL = {
    "extract_dim": [
        ">>> Mulai ETL Dimensi (Incremental Load)...",
        "Kolom nasabah: ['nasabah_code', 'nama_lengkap', 'tanggal_lahir', 'jenis_kelamin', 'segmen_nasabah']",
    ],
    "transform_waktu": [
        "    dim_waktu      : 10957 baris",
    ],
    "transform_nasabah": [
        "    dim_nasabah    : 1001 baris (termasuk Unknown)",
    ],
    "transform_merchant": [
        "    dim_merchant   : 101 baris (termasuk Unknown)",
    ],
    "transform_channel": [
        "    dim_channel    : 6 baris (termasuk Unknown)",
    ],
    "transform_wilayah": [
        "    dim_wilayah    : 17 baris (termasuk Unknown)",
    ],
    "load_dimensi": [
        "    -> Cek & insert data baru...",
        "    dim_nasabah  : +83 baris baru",
        "    dim_merchant : +12 baris baru",
        ">>> Dimensi (Incremental) SELESAI!",
    ],
    "transform_fakta": [
        ">>> Mulai ETL Fakta (Incremental Load)...",
        "    Membersihkan nominal, membuang duplikat & baris tidak valid...",
    ],
    "validate_fakta": [
        "    Watermark waktu_id saat ini: 20260411",
        "    Total baris fakta baru siap insert: 9345",
    ],
    "load_fakta": [
        "    -> Insert ke tabel fakta...",
        ">>> Fakta (Incremental) SELESAI!",
    ],
    "mvw": [
        ">>> Membuat Materialized View untuk Looker Studio di Aiven...",
        "✓ Materialized View berhasil dibuat di Aiven!",
    ],
}

_lock = threading.Lock()
_state = {
    "status": "idle",  # idle | running | success | error
    "mode": None,
    "steps": [],
    "logs": [],
    "started_at": None,
    "finished_at": None,
}


def _reset_state(mode):
    steps = FULL_STEPS if mode == "full" else INCREMENTAL_STEPS
    _state["status"] = "running"
    _state["mode"] = mode
    _state["steps"] = [{**s, "status": "pending"} for s in steps]
    _state["logs"] = []
    _state["started_at"] = time.time()
    _state["finished_at"] = None


def _append_log(line):
    with _lock:
        _state["logs"].append(line)
        if len(_state["logs"]) > 500:
            _state["logs"] = _state["logs"][-500:]


def _run_simulation(mode):
    """Jalankan simulasi pipeline secara bertahap: tiap step ditandai
    'running' -> tampilkan log tiruan satu per satu -> tandai 'success'.
    Diberi jeda acak supaya terasa seperti proses yang sedang berjalan."""
    sim_logs = SIM_LOGS_FULL if mode == "full" else SIM_LOGS_INCREMENTAL

    with _lock:
        steps = _state["steps"]

    for step in steps:
        with _lock:
            step["status"] = "running"
        time.sleep(random.uniform(0.35, 0.6))

        for line in sim_logs.get(step["key"], []):
            _append_log(line)
            time.sleep(random.uniform(0.12, 0.25))

        with _lock:
            step["status"] = "success"
        time.sleep(random.uniform(0.15, 0.3))

    with _lock:
        _state["status"] = "success"
        _state["finished_at"] = time.time()


def start_etl(mode):
    """Mulai simulasi pipeline ETL ('full'/'incremental') di thread terpisah.
    Return False jika ada simulasi yang masih berjalan."""
    if mode not in ("full", "incremental"):
        raise ValueError("mode harus 'full' atau 'incremental'")

    with _lock:
        if _state["status"] == "running":
            return False
        _reset_state(mode)

    threading.Thread(target=_run_simulation, args=(mode,), daemon=True).start()
    return True


def get_state():
    with _lock:
        return {
            "status": _state["status"],
            "mode": _state["mode"],
            "steps": [dict(s) for s in _state["steps"]],
            "logs": list(_state["logs"]),
            "started_at": _state["started_at"],
            "finished_at": _state["finished_at"],
        }
