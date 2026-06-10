# dashboard/backend/main.py
# FastAPI sederhana yang menjembatani frontend dashboard <-> atoti OLAP Cube.
#
# Semua filter global (tahun, quarter, bulan, rentang tanggal, channel,
# segmen nasabah, kategori merchant, provinsi, kota) dikirim sebagai query
# params dan diteruskan ke cube_service.build_filter() -> cube.query().
#
# Jalankan:
#   source ../../.venv_atoti/bin/activate
#   export ATOTI_HIDE_EULA_MESSAGE=True
#   uvicorn main:app --reload --port 8000

import asyncio
import json
from typing import List, Optional

from fastapi import Depends, FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

import cube_service as cs
import etl_runner as etl

app = FastAPI(title="Dashboard Transaksi Mandiri API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _filter_params(
    tahun: Optional[List[int]] = Query(None),
    quarter: Optional[List[str]] = Query(None),
    bulan: Optional[List[str]] = Query(None),
    channel: Optional[List[str]] = Query(None),
    segmen: Optional[List[str]] = Query(None),
    kategori: Optional[List[str]] = Query(None),
    provinsi: Optional[List[str]] = Query(None),
    kota: Optional[List[str]] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    include_unknown: bool = Query(False),
) -> dict:
    return {
        "tahun": tahun, "quarter": quarter, "bulan": bulan,
        "channel": channel, "segmen": segmen, "kategori": kategori,
        "provinsi": provinsi, "kota": kota,
        "start_date": start_date, "end_date": end_date,
        "include_unknown": include_unknown,
    }


@app.on_event("startup")
def _warm_up_cube():
    # Bangun cube sekali saat startup supaya request pertama tidak lambat.
    cs.get_cube()


@app.get("/api/filters/options")
def filters_options():
    return cs.get_filter_options()


@app.post("/api/cube/refresh")
def cube_refresh():
    """Bangun ulang cube atoti dari data terbaru di database (dipanggil
    setelah ETL baru di-load supaya dashboard tidak menampilkan data lama)."""
    cs.refresh_cube()
    return {"refreshed": True}


@app.get("/api/kpi")
def kpi(p: dict = Depends(_filter_params)):
    return cs.get_kpi(p)


@app.get("/api/monthly-trend")
def monthly_trend(p: dict = Depends(_filter_params)):
    return cs.get_monthly_trend(p)


@app.get("/api/channel-distribution")
def channel_distribution(p: dict = Depends(_filter_params)):
    return cs.get_channel_distribution(p)


@app.get("/api/customer-segment")
def customer_segment(p: dict = Depends(_filter_params)):
    return cs.get_customer_segment(p)


@app.get("/api/merchant-category")
def merchant_category(p: dict = Depends(_filter_params)):
    return cs.get_merchant_category(p)


@app.get("/api/top-merchants")
def top_merchants(limit: int = 10, p: dict = Depends(_filter_params)):
    return cs.get_top_merchants(p, limit=limit)


@app.get("/api/geographic")
def geographic(p: dict = Depends(_filter_params)):
    return cs.get_geographic(p)


@app.get("/api/city-ranking")
def city_ranking(p: dict = Depends(_filter_params)):
    return cs.get_city_ranking(p)


@app.get("/api/gender-distribution")
def gender_distribution(p: dict = Depends(_filter_params)):
    return cs.get_gender_distribution(p)


@app.get("/api/channel-by-region")
def channel_by_region(p: dict = Depends(_filter_params)):
    return cs.get_channel_by_region(p)


@app.get("/api/daily-transaction")
def daily_transaction(p: dict = Depends(_filter_params)):
    return cs.get_daily_transaction(p)


@app.get("/api/heatmap")
def heatmap(p: dict = Depends(_filter_params)):
    return cs.get_heatmap(p)


# ---------------------------------------------------------------------------
# ETL MONITOR — menjalankan main.py (root) sebagai subprocess & melacak progres
# secara real-time. Tidak menyentuh kode di etl/ maupun main.py.
# ---------------------------------------------------------------------------
@app.post("/api/etl/run")
def etl_run(mode: str = Query("full")):
    if mode not in ("full", "incremental"):
        return {"started": False, "message": "Mode harus 'full' atau 'incremental'"}
    started = etl.start_etl(mode)
    if not started:
        return {"started": False, "message": "ETL sedang berjalan"}
    return {"started": True}


@app.get("/api/etl/status")
def etl_status():
    return etl.get_state()


@app.get("/api/etl/stream")
async def etl_stream(request: Request):
    async def event_gen():
        last_snapshot = None
        while True:
            if await request.is_disconnected():
                break
            state = etl.get_state()
            snapshot = json.dumps(state)
            if snapshot != last_snapshot:
                last_snapshot = snapshot
                yield f"data: {snapshot}\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(event_gen(), media_type="text/event-stream")
