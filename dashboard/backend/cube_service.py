# dashboard/backend/cube_service.py
# Wrapper di atas analytics/cube.py: bangun cube sekali (singleton),
# lalu sediakan fungsi query per-chart yang dipakai endpoint FastAPI.
#
# Semua agregasi (slice/dice/drill-down/roll-up) dilakukan oleh atoti
# (cube.query), bukan oleh frontend.

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from analytics.cube import build_cube

MONTH_ORDER = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Koordinat kota untuk peta interaktif (data saat ini hanya mencakup kota-kota ini)
CITY_COORDS = {
    "Bandung": (-6.9175, 107.6191),
    "Jakarta Selatan": (-6.2615, 106.8106),
    "Surabaya": (-7.2575, 112.7521),
    "Medan": (3.5952, 98.6722),
    "Yogyakarta": (-7.7956, 110.3695),
    "Unknown": (-2.5489, 118.0149),
}

_session = None
_cube = None


def get_cube():
    """Bangun atoti session+cube sekali saja (lazy singleton)."""
    global _session, _cube
    if _cube is None:
        _session, _cube = build_cube()
    return _cube


def refresh_cube():
    """Tutup session atoti lama (jika ada) lalu bangun ulang cube dari data
    terbaru di database. Dipanggil lewat endpoint POST /api/cube/refresh
    setelah ada batch ETL baru yang di-load."""
    global _session, _cube
    if _session is not None:
        _session.close()
    _session, _cube = build_cube()
    return _cube


def build_filter(cube, params: dict):
    """Gabungkan parameter filter global jadi satu kondisi atoti.
    Mendukung slice (1 nilai) & dice (banyak nilai) karena semua pakai isin()."""
    l = cube.levels
    cond = None
    included_hierarchies = set()

    def add(level_key, values):
        nonlocal cond
        if values:
            c = l[level_key].isin(*values)
            cond = c if cond is None else cond & c
            included_hierarchies.add(level_key[0])

    add(("Waktu", "tahun"), params.get("tahun"))
    add(("Waktu", "quarter"), params.get("quarter"))
    add(("Waktu", "bulan"), params.get("bulan"))
    add(("Channel", "nama_channel"), params.get("channel"))
    add(("Nasabah", "segmen_nasabah"), params.get("segmen"))
    add(("Merchant", "kategori"), params.get("kategori"))
    add(("Wilayah", "provinsi"), params.get("provinsi"))
    add(("Wilayah", "kota"), params.get("kota"))

    start_date = params.get("start_date")
    end_date = params.get("end_date")
    if start_date:
        c = l["Waktu", "tanggal"] >= start_date
        cond = c if cond is None else cond & c
    if end_date:
        c = l["Waktu", "tanggal"] <= end_date
        cond = c if cond is None else cond & c

    # Secara default, baris "Unknown" (placeholder untuk dimensi yang tidak
    # tercatat di sumber data) disembunyikan kecuali include_unknown=True.
    if not params.get("include_unknown"):
        # Lewati exclusion filter untuk hierarchy yang sudah punya inclusion
        # filter (isin) dari user -- atoti tidak bisa menggabungkan inclusion
        # & exclusion filter pada hierarchy yang sama ("Only exclusion filters
        # can be combined"), dan nilai pilihan user pasti bukan "Unknown".
        for level_key in (
            ("Waktu", "quarter"), ("Waktu", "bulan"), ("Hari Transaksi", "hari"),
            ("Nasabah", "segmen_nasabah"), ("Nasabah", "jenis_kelamin"), ("Nasabah", "nama_lengkap"),
            ("Channel", "jenis_channel"), ("Channel", "nama_channel"),
            ("Wilayah", "region"), ("Wilayah", "provinsi"), ("Wilayah", "kota"),
            ("Merchant", "kategori"), ("Merchant", "nama_merchant"),
        ):
            if level_key[0] in included_hierarchies:
                continue
            c = l[level_key] != "Unknown"
            cond = c if cond is None else cond & c
        if "Nasabah" not in included_hierarchies:
            c = l["Nasabah", "jenis_kelamin"] != "U"
            cond = c if cond is None else cond & c
        if "Waktu" not in included_hierarchies:
            c = l["Waktu", "tahun"] != 0
            cond = c if cond is None else cond & c

    return cond


def _df(cube, levels, measures, filter_cond):
    """Helper: jalankan cube.query dan return DataFrame hasil (mode='raw').

    Kalau kombinasi filter tidak match baris apapun, atoti raw mode
    mengembalikan DataFrame tanpa kolom level (hanya kolom measure) --
    tambahkan kembali kolom level (kosong) supaya kode pemanggil yang
    mengakses df[nama_level] tidak KeyError."""
    l = cube.levels
    level_objs = [l[k] for k in levels]
    measure_objs = [cube.measures[m] for m in measures]
    kwargs = {"mode": "raw"}
    if filter_cond is not None:
        kwargs["filter"] = filter_cond
    if level_objs:
        df = cube.query(*measure_objs, levels=level_objs, **kwargs)
        for _, level_name in levels:
            if level_name not in df.columns:
                df[level_name] = pd.Series(dtype="object")
        return df
    return cube.query(*measure_objs, **kwargs)


def _num(val, cast=float):
    """Konversi nilai measure atoti ke tipe Python, treat NA/NaN sebagai 0
    (terjadi saat filter tidak match baris apapun)."""
    return cast(0) if pd.isna(val) else cast(val)


# ---------------------------------------------------------------------------
# FILTER OPTIONS — dipakai untuk mengisi dropdown filter global
# ---------------------------------------------------------------------------
def get_filter_options():
    cube = get_cube()
    l = cube.levels
    m = cube.measures

    df_waktu = _df(cube, [("Waktu", "tahun")], ["Jumlah Transaksi"], None)
    tahun = sorted(int(x) for x in df_waktu["tahun"].dropna().unique().tolist())

    df_quarter = _df(cube, [("Waktu", "quarter")], ["Jumlah Transaksi"], None)
    quarter = sorted(df_quarter["quarter"].dropna().unique().tolist())

    df_bulan = _df(cube, [("Waktu", "bulan")], ["Jumlah Transaksi"], None)
    bulan = [b for b in MONTH_ORDER if b in set(df_bulan["bulan"].dropna().unique().tolist())]

    df_channel = _df(cube, [("Channel", "nama_channel")], ["Jumlah Transaksi"], None)
    channel = sorted(df_channel["nama_channel"].dropna().unique().tolist())

    df_segmen = _df(cube, [("Nasabah", "segmen_nasabah")], ["Jumlah Transaksi"], None)
    segmen = sorted(df_segmen["segmen_nasabah"].dropna().unique().tolist())

    df_kategori = _df(cube, [("Merchant", "kategori")], ["Jumlah Transaksi"], None)
    kategori = sorted(df_kategori["kategori"].dropna().unique().tolist())

    df_wilayah = _df(cube, [("Wilayah", "provinsi"), ("Wilayah", "kota")], ["Jumlah Transaksi"], None)
    provinsi = sorted(df_wilayah["provinsi"].dropna().unique().tolist())
    kota = sorted(df_wilayah["kota"].dropna().unique().tolist())

    df_tanggal = _df(cube, [("Waktu", "tanggal")], ["Jumlah Transaksi"], None)
    tanggal_series = df_tanggal["tanggal"].dropna()
    min_date = tanggal_series.min()
    max_date = tanggal_series.max()

    return {
        "tahun": tahun,
        "quarter": quarter,
        "bulan": bulan,
        "channel": channel,
        "segmen": segmen,
        "kategori": kategori,
        "provinsi": provinsi,
        "kota": kota,
        "min_date": str(min_date) if min_date is not None else None,
        "max_date": str(max_date) if max_date is not None else None,
    }


# ---------------------------------------------------------------------------
# 0. KPI
# ---------------------------------------------------------------------------
def get_kpi(params: dict):
    cube = get_cube()
    cond = build_filter(cube, params)
    df = _df(cube, [], [
        "Total Volume Transaksi", "Jumlah Transaksi",
        "Total Biaya Admin", "Rata-rata Nominal Transaksi",
    ], cond)
    row = df.iloc[0]
    current = {
        "total_volume_transaksi": _num(row["Total Volume Transaksi"]),
        "total_frekuensi_transaksi": _num(row["Jumlah Transaksi"], cast=int),
        "total_revenue_transaksi": _num(row["Total Biaya Admin"]),
        "avg_nominal_transaksi": _num(row["Rata-rata Nominal Transaksi"]),
    }

    # Trend (MoM) hanya dihitung kalau filter tahun+bulan persis 1 nilai
    trend = None
    tahun_list = params.get("tahun") or []
    bulan_list = params.get("bulan") or []
    if len(tahun_list) == 1 and len(bulan_list) == 1:
        tahun = int(tahun_list[0])
        bulan_idx = MONTH_ORDER.index(bulan_list[0])
        if bulan_idx == 0:
            prev_tahun, prev_bulan = tahun - 1, MONTH_ORDER[11]
        else:
            prev_tahun, prev_bulan = tahun, MONTH_ORDER[bulan_idx - 1]

        prev_params = dict(params)
        prev_params["tahun"] = [prev_tahun]
        prev_params["bulan"] = [prev_bulan]
        prev_cond = build_filter(cube, prev_params)
        df_prev = _df(cube, [], [
            "Total Volume Transaksi", "Jumlah Transaksi",
            "Total Biaya Admin", "Rata-rata Nominal Transaksi",
        ], prev_cond)
        prev_row = df_prev.iloc[0]

        def pct(curr_val, prev_val):
            if not prev_val:
                return None
            return round((curr_val - prev_val) / prev_val * 100, 2)

        trend = {
            "total_volume_transaksi": pct(current["total_volume_transaksi"], _num(prev_row["Total Volume Transaksi"])),
            "total_frekuensi_transaksi": pct(current["total_frekuensi_transaksi"], _num(prev_row["Jumlah Transaksi"])),
            "total_revenue_transaksi": pct(current["total_revenue_transaksi"], _num(prev_row["Total Biaya Admin"])),
            "avg_nominal_transaksi": pct(current["avg_nominal_transaksi"], _num(prev_row["Rata-rata Nominal Transaksi"])),
        }

    return {**current, "trend": trend}


# ---------------------------------------------------------------------------
# 1. MONTHLY TRANSACTION TREND (drill-down ke harian jika tahun+bulan dipilih)
# ---------------------------------------------------------------------------
def get_monthly_trend(params: dict):
    cube = get_cube()
    cond = build_filter(cube, params)

    tahun_list = params.get("tahun") or []
    bulan_list = params.get("bulan") or []
    if len(tahun_list) == 1 and len(bulan_list) == 1:
        # DRILL DOWN -> harian dalam bulan terpilih
        df = _df(cube, [("Waktu", "tanggal")],
                 ["Total Volume Transaksi", "Jumlah Transaksi"], cond)
        df = df.sort_values("tanggal")
        return {
            "granularity": "day",
            "data": [
                {
                    "label": row["tanggal"].strftime("%Y-%m-%d"),
                    "total_volume_transaksi": float(row["Total Volume Transaksi"]),
                    "jumlah_transaksi": int(row["Jumlah Transaksi"]),
                }
                for _, row in df.iterrows()
            ],
        }

    # ROLL UP -> per bulan (urut kronologis: tahun lalu bulan)
    df = _df(cube, [("Waktu", "tahun"), ("Waktu", "bulan")],
             ["Total Volume Transaksi", "Jumlah Transaksi"], cond)
    df["__bulan_idx"] = df["bulan"].apply(lambda b: MONTH_ORDER.index(b))
    df = df.sort_values(["tahun", "__bulan_idx"])
    return {
        "granularity": "month",
        "data": [
            {
                "label": f"{row['bulan'][:3]} {int(row['tahun'])}",
                "total_volume_transaksi": float(row["Total Volume Transaksi"]),
                "jumlah_transaksi": int(row["Jumlah Transaksi"]),
            }
            for _, row in df.iterrows()
        ],
    }


# ---------------------------------------------------------------------------
# 2. CHANNEL DISTRIBUTION (donut)
# ---------------------------------------------------------------------------
def get_channel_distribution(params: dict):
    cube = get_cube()
    cond = build_filter(cube, params)
    df = _df(cube, [("Nama Channel", "nama_channel")],
             ["Total Volume Transaksi", "Jumlah Transaksi"], cond)
    df = df.sort_values("Total Volume Transaksi", ascending=False)
    return [
        {
            "channel": row["nama_channel"],
            "total_volume_transaksi": float(row["Total Volume Transaksi"]),
            "jumlah_transaksi": int(row["Jumlah Transaksi"]),
        }
        for _, row in df.iterrows()
    ]


# ---------------------------------------------------------------------------
# 3. CUSTOMER SEGMENT CONTRIBUTION (donut)
# ---------------------------------------------------------------------------
def get_customer_segment(params: dict):
    cube = get_cube()
    cond = build_filter(cube, params)
    df = _df(cube, [("Nasabah", "segmen_nasabah")],
             ["Total Volume Transaksi", "Jumlah Transaksi"], cond)
    df = df.sort_values("Total Volume Transaksi", ascending=False)
    return [
        {
            "segmen": row["segmen_nasabah"],
            "total_volume_transaksi": float(row["Total Volume Transaksi"]),
            "jumlah_transaksi": int(row["Jumlah Transaksi"]),
        }
        for _, row in df.iterrows()
    ]


# ---------------------------------------------------------------------------
# 4. MERCHANT CATEGORY RANKING (bar)
# ---------------------------------------------------------------------------
def get_merchant_category(params: dict):
    cube = get_cube()
    cond = build_filter(cube, params)
    df = _df(cube, [("Merchant", "kategori")],
             ["Total Volume Transaksi", "Jumlah Transaksi"], cond)
    df = df.sort_values("Total Volume Transaksi", ascending=False)
    return [
        {
            "kategori": row["kategori"],
            "total_volume_transaksi": float(row["Total Volume Transaksi"]),
            "jumlah_transaksi": int(row["Jumlah Transaksi"]),
        }
        for _, row in df.iterrows()
    ]


# ---------------------------------------------------------------------------
# 5. TOP MERCHANT ANALYSIS (horizontal bar / data table)
# ---------------------------------------------------------------------------
def get_top_merchants(params: dict, limit: int = 10):
    cube = get_cube()
    cond = build_filter(cube, params)
    df = _df(cube, [("Merchant", "kategori"), ("Merchant", "nama_merchant")],
             ["Total Volume Transaksi", "Jumlah Transaksi"], cond)
    df = df.sort_values("Total Volume Transaksi", ascending=False).head(limit)
    return [
        {
            "nama_merchant": row["nama_merchant"],
            "kategori": row["kategori"],
            "total_volume_transaksi": float(row["Total Volume Transaksi"]),
            "jumlah_transaksi": int(row["Jumlah Transaksi"]),
        }
        for _, row in df.iterrows()
    ]


# ---------------------------------------------------------------------------
# 6. GEOGRAPHIC TRANSACTION ANALYSIS (peta interaktif)
# ---------------------------------------------------------------------------
def get_geographic(params: dict):
    cube = get_cube()
    cond = build_filter(cube, params)
    df = _df(cube, [("Wilayah", "provinsi"), ("Wilayah", "kota")],
             ["Total Volume Transaksi", "Jumlah Transaksi"], cond)
    result = []
    for _, row in df.iterrows():
        kota = row["kota"]
        lat, lon = CITY_COORDS.get(kota, CITY_COORDS["Unknown"])
        result.append({
            "provinsi": row["provinsi"],
            "kota": kota,
            "lat": lat,
            "lon": lon,
            "total_volume_transaksi": float(row["Total Volume Transaksi"]),
            "jumlah_transaksi": int(row["Jumlah Transaksi"]),
        })
    return result


# ---------------------------------------------------------------------------
# 7. CITY RANKING (horizontal bar)
# ---------------------------------------------------------------------------
def get_city_ranking(params: dict):
    cube = get_cube()
    cond = build_filter(cube, params)
    df = _df(cube, [("Wilayah", "kota")],
             ["Total Volume Transaksi", "Jumlah Transaksi"], cond)
    df = df.sort_values("Total Volume Transaksi", ascending=False)
    return [
        {
            "kota": row["kota"],
            "total_volume_transaksi": float(row["Total Volume Transaksi"]),
            "jumlah_transaksi": int(row["Jumlah Transaksi"]),
        }
        for _, row in df.iterrows()
    ]


# ---------------------------------------------------------------------------
# 8. GENDER DISTRIBUTION (donut)
# ---------------------------------------------------------------------------
def get_gender_distribution(params: dict):
    cube = get_cube()
    cond = build_filter(cube, params)
    df = _df(cube, [("Nasabah", "jenis_kelamin")],
             ["Total Volume Transaksi", "Jumlah Transaksi"], cond)
    # "jenis_kelamin" bukan level teratas hierarchy "Nasabah" (di bawah
    # segmen_nasabah), jadi atoti bisa mengembalikan baris duplikat per
    # kombinasi segmen_nasabah -> jumlahkan ulang per gender.
    df = df.groupby("jenis_kelamin", as_index=False)[
        ["Total Volume Transaksi", "Jumlah Transaksi"]
    ].sum()
    return [
        {
            "jenis_kelamin": row["jenis_kelamin"],
            "total_volume_transaksi": float(row["Total Volume Transaksi"]),
            "jumlah_transaksi": int(row["Jumlah Transaksi"]),
        }
        for _, row in df.iterrows()
    ]


# ---------------------------------------------------------------------------
# 9. CHANNEL USAGE BY REGION (stacked bar)
# ---------------------------------------------------------------------------
def get_channel_by_region(params: dict):
    cube = get_cube()
    cond = build_filter(cube, params)
    df = _df(cube, [("Wilayah", "kota"), ("Nama Channel", "nama_channel")],
             ["Jumlah Transaksi"], cond)

    pivot = df.pivot_table(
        index="kota", columns="nama_channel", values="Jumlah Transaksi",
        aggfunc="sum", fill_value=0,
    )
    channels = sorted(pivot.columns.tolist())
    result = []
    for kota, row in pivot.iterrows():
        item = {"kota": kota}
        for ch in channels:
            item[ch] = int(row[ch])
        result.append(item)
    return {"channels": channels, "data": result}


# ---------------------------------------------------------------------------
# 10. DAILY TRANSACTION ANALYSIS (peak transaction day)
# ---------------------------------------------------------------------------
def get_daily_transaction(params: dict):
    cube = get_cube()
    cond = build_filter(cube, params)
    df = _df(cube, [("Hari Transaksi", "hari")],
             ["Total Volume Transaksi", "Jumlah Transaksi"], cond)
    df["__idx"] = df["hari"].apply(lambda h: DAY_ORDER.index(h))
    df = df.sort_values("__idx")
    return [
        {
            "hari": row["hari"],
            "total_volume_transaksi": float(row["Total Volume Transaksi"]),
            "jumlah_transaksi": int(row["Jumlah Transaksi"]),
        }
        for _, row in df.iterrows()
    ]


# ---------------------------------------------------------------------------
# 11. HEATMAP — Bulan x Hari (Jumlah Transaksi)
# ---------------------------------------------------------------------------
def get_heatmap(params: dict):
    cube = get_cube()
    cond = build_filter(cube, params)
    df = _df(cube, [("Waktu", "bulan"), ("Hari Transaksi", "hari")],
             ["Jumlah Transaksi"], cond)

    bulan_present = [b for b in MONTH_ORDER if b in set(df["bulan"].unique().tolist())]
    pivot = df.pivot_table(
        index="bulan", columns="hari", values="Jumlah Transaksi",
        aggfunc="sum", fill_value=0,
    )
    result = []
    for bulan in bulan_present:
        row = pivot.loc[bulan]
        for hari in DAY_ORDER:
            result.append({
                "bulan": bulan,
                "hari": hari,
                "jumlah_transaksi": int(row.get(hari, 0)),
            })
    return {"bulan": bulan_present, "hari": DAY_ORDER, "data": result}
