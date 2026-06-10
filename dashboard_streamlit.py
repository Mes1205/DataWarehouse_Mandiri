# dashboard_streamlit.py
# Dashboard analitik transaksi digital banking Bank Mandiri — 100% kode,
# TANPA drag-and-drop Atoti Web UI.
#
# Kenapa pendekatan ini:
#   Atoti Web App (yang URL-nya dicetak oleh olap_cube_atoti.py) memang
#   menyediakan dashboard, tapi widget-nya (pivot table, chart) dibuat lewat
#   drag-and-drop di browser dan disimpan di sisi server Atoti — bukan lewat
#   kode Python.
#
#   Namun atoti tetap menyediakan cube.query(), yang mengembalikan hasil
#   agregasi OLAP sebagai pandas DataFrame biasa. DataFrame ini bisa
#   dirender dengan library apa pun. Di sini dipakai:
#     - Streamlit  -> layout halaman, KPI cards, sidebar filter
#     - Plotly     -> chart (pie/donut, bar, line, stacked bar)
#
#   Hasilnya: dashboard custom, full-code, dan tetap mendapat keuntungan
#   atoti sebagai mesin OLAP in-memory (cube dibangun sekali, lalu setiap
#   interaksi filter di sidebar memanggil cube.query() yang sangat cepat
#   karena tidak perlu query ulang ke PostgreSQL).
#
# Struktur dashboard mengikuti Section IV.G paper (1-7):
#   1. High-Level KPI
#   2. Digital Channel Analytics
#   3. Customer Segmentation
#   4. Merchant Ecosystem
#   5. Geographic Analytics
#   6. Time-Series Analytics (tren bulanan + peak transaction day)
#   7. Regional Channel Utilization
#
# Cara pakai:
#   source .venv_atoti/bin/activate
#   export ATOTI_HIDE_EULA_MESSAGE=True
#   streamlit run dashboard_streamlit.py

import plotly.express as px
import streamlit as st

from olap_cube_atoti import build_cube

st.set_page_config(
    page_title="Dashboard Transaksi Digital - Bank Mandiri",
    page_icon="🏦",
    layout="wide",
)


@st.cache_resource(show_spinner="Membangun OLAP cube (load data dari PostgreSQL)...")
def get_cube():
    """Bangun session + cube sekali saja, lalu di-cache selama app Streamlit
    hidup. Tanpa cache_resource, build_cube() (yang query ke Postgres dan
    membangun cube in-memory) akan terulang setiap kali user mengganti
    filter di sidebar."""
    return build_cube()


session, cube = get_cube()
l, m = cube.levels, cube.measures


@st.cache_data(show_spinner=False)
def distinct_members(level_name):
    """Ambil semua nilai unik sebuah level — dipakai untuk mengisi pilihan
    multiselect di sidebar."""
    df = cube.query(m["Jumlah Transaksi"], levels=[l[level_name]], mode="raw")
    return sorted(df[level_name].dropna().unique().tolist())


def build_filter(selections):
    """Gabungkan beberapa filter sidebar jadi satu kondisi atoti.

    selections: list of (level_name, selected_values, all_values)

    Catatan: Level.isin() menerima *args (variadic), bukan list, jadi
    list hasil multiselect harus di-unpack dengan '*'. Jika user memilih
    semua opsi (atau tidak memilih sama sekali), dimensi tersebut dilewati
    -> tidak memfilter apa pun (sama dengan "tampilkan semua")."""
    cond = None
    for level_name, selected, all_values in selections:
        if 0 < len(selected) < len(all_values):
            level_cond = l[level_name].isin(*selected)
            cond = level_cond if cond is None else cond & level_cond
    return cond


# =====================================================================
# SIDEBAR — FILTER
# =====================================================================
st.sidebar.title("🔍 Filter Dashboard")

all_segmen = distinct_members("segmen_nasabah")
all_channel = distinct_members("nama_channel")
all_kota = distinct_members("kota")

sel_segmen = st.sidebar.multiselect("Segmen Nasabah", all_segmen, default=all_segmen)
sel_channel = st.sidebar.multiselect("Channel", all_channel, default=all_channel)
sel_kota = st.sidebar.multiselect("Kota", all_kota, default=all_kota)

FILTER = build_filter([
    ("segmen_nasabah", sel_segmen, all_segmen),
    ("nama_channel", sel_channel, all_channel),
    ("kota", sel_kota, all_kota),
])


# =====================================================================
# 1. HIGH-LEVEL KPI
# =====================================================================
st.title("🏦 Dashboard Transaksi Digital Banking - Bank Mandiri")
st.caption(
    "PostgreSQL (Star Schema) -> atoti OLAP Cube -> Streamlit + Plotly "
    "(100% kode, tanpa drag-and-drop)."
)

kpi_df = cube.query(
    m["Total Volume Transaksi"],
    m["Jumlah Transaksi"],
    m["Total Biaya Admin"],
    m["Rata-rata Nominal Transaksi"],
    filter=FILTER,
    mode="raw",
)

if kpi_df.empty:
    st.warning("Tidak ada data untuk kombinasi filter ini.")
    st.stop()

kpi = kpi_df.iloc[0]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Volume Transaksi", f"Rp {kpi['Total Volume Transaksi']:,.0f}")
c2.metric("Jumlah Transaksi", f"{kpi['Jumlah Transaksi']:,.0f}")
c3.metric("Total Biaya Admin", f"Rp {kpi['Total Biaya Admin']:,.0f}")
c4.metric("Rata-rata Nominal Transaksi", f"Rp {kpi['Rata-rata Nominal Transaksi']:,.0f}")

st.divider()


# =====================================================================
# 2. DIGITAL CHANNEL ANALYTICS
# =====================================================================
st.subheader("📡 Digital Channel Analytics")

df_channel = cube.query(
    m["Total Volume Transaksi"], m["Jumlah Transaksi"],
    levels=[l["nama_channel"]], filter=FILTER, mode="raw",
)

col1, col2 = st.columns(2)
with col1:
    fig = px.pie(
        df_channel, names="nama_channel", values="Total Volume Transaksi",
        hole=0.45, title="Distribusi Volume Transaksi per Channel",
    )
    st.plotly_chart(fig, use_container_width=True)
with col2:
    fig = px.pie(
        df_channel, names="nama_channel", values="Jumlah Transaksi",
        hole=0.45, title="Distribusi Jumlah Transaksi per Channel",
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()


# =====================================================================
# 3. CUSTOMER SEGMENTATION
# =====================================================================
st.subheader("👥 Customer Segmentation")

df_segmen = cube.query(
    m["Total Volume Transaksi"], levels=[l["segmen_nasabah"]], filter=FILTER, mode="raw",
)
df_gender = cube.query(
    m["Total Volume Transaksi"], levels=[l["jenis_kelamin"]], filter=FILTER, mode="raw",
)

col1, col2 = st.columns(2)
with col1:
    fig = px.pie(
        df_segmen, names="segmen_nasabah", values="Total Volume Transaksi",
        hole=0.45, title="Volume Transaksi per Segmen Nasabah",
    )
    st.plotly_chart(fig, use_container_width=True)
with col2:
    fig = px.pie(
        df_gender, names="jenis_kelamin", values="Total Volume Transaksi",
        hole=0.45, title="Volume Transaksi per Jenis Kelamin",
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()


# =====================================================================
# 4. MERCHANT ECOSYSTEM
# =====================================================================
st.subheader("🏪 Merchant Ecosystem")

df_kategori = cube.query(
    m["Total Volume Transaksi"], levels=[l["kategori"]], filter=FILTER, mode="raw",
).sort_values("Total Volume Transaksi", ascending=False)

df_merchant = cube.query(
    m["Total Volume Transaksi"], m["Jumlah Transaksi"],
    levels=[l["nama_merchant"]], filter=FILTER, mode="raw",
).sort_values("Total Volume Transaksi", ascending=False).head(10)

col1, col2 = st.columns(2)
with col1:
    fig = px.bar(
        df_kategori, x="kategori", y="Total Volume Transaksi",
        title="Volume Transaksi per Kategori Merchant",
    )
    st.plotly_chart(fig, use_container_width=True)
with col2:
    st.write("**Top 10 Merchant - Volume Transaksi**")
    st.dataframe(
        df_merchant[["nama_merchant", "Total Volume Transaksi", "Jumlah Transaksi"]],
        use_container_width=True, hide_index=True,
    )

st.divider()


# =====================================================================
# 5. GEOGRAPHIC ANALYTICS
# =====================================================================
st.subheader("📍 Geographic Analytics")

df_kota = cube.query(
    m["Total Volume Transaksi"], m["Jumlah Transaksi"],
    levels=[l["kota"]], filter=FILTER, mode="raw",
).sort_values("Total Volume Transaksi", ascending=False)

fig = px.bar(
    df_kota, x="kota", y="Total Volume Transaksi", color="kota",
    title="Volume Transaksi per Kota",
)
st.plotly_chart(fig, use_container_width=True)

st.divider()


# =====================================================================
# 6. TIME-SERIES ANALYTICS
# =====================================================================
st.subheader("📈 Time-Series Analytics")

col1, col2 = st.columns(2)

with col1:
    df_bulan = cube.query(
        m["Total Volume Transaksi"], m["Jumlah Transaksi"],
        levels=[l["bulan"]], filter=FILTER, mode="raw",
    )
    fig = px.line(
        df_bulan, x="bulan", y="Total Volume Transaksi", markers=True,
        title="Tren Volume Transaksi per Bulan",
    )
    # df_bulan sudah terurut kronologis (Januari -> Desember) berkat
    # tt.CustomOrder di olap_cube_atoti.py. categoryorder="array" memastikan
    # Plotly tidak mengurutkan ulang sumbu-x secara alfabetis.
    fig.update_xaxes(categoryorder="array", categoryarray=df_bulan["bulan"].tolist())
    st.plotly_chart(fig, use_container_width=True)

with col2:
    df_hari = cube.query(
        m["Jumlah Transaksi"], levels=[l["hari"]], filter=FILTER, mode="raw",
    )
    fig = px.bar(
        df_hari, x="hari", y="Jumlah Transaksi",
        title="Peak Transaction Day (Jumlah Transaksi per Hari)",
    )
    fig.update_xaxes(categoryorder="array", categoryarray=df_hari["hari"].tolist())
    st.plotly_chart(fig, use_container_width=True)

st.divider()


# =====================================================================
# 7. REGIONAL CHANNEL UTILIZATION
# =====================================================================
st.subheader("🗺️ Regional Channel Utilization")

df_region_channel = cube.query(
    m["Jumlah Transaksi"],
    levels=[l["kota"], l["nama_channel"]], filter=FILTER, mode="raw",
)

fig = px.bar(
    df_region_channel, x="kota", y="Jumlah Transaksi", color="nama_channel",
    barmode="stack", title="Jumlah Transaksi per Kota x Channel",
)
st.plotly_chart(fig, use_container_width=True)
