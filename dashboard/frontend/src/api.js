import axios from "axios";

const client = axios.create({
  baseURL: "http://127.0.0.1:8000/api",
  // FastAPI mengharapkan array sebagai repeated key (?tahun=2026&tahun=2027),
  // bukan format "tahun[]=2026" yang dipakai default serializer axios.
  paramsSerializer: {
    serialize: (params) => {
      const search = new URLSearchParams();
      for (const [key, value] of Object.entries(params)) {
        if (Array.isArray(value)) {
          value.forEach((v) => search.append(key, v));
        } else {
          search.append(key, value);
        }
      }
      return search.toString();
    },
  },
});

// Buang key dengan value null/undefined/[] supaya query string bersih.
function cleanParams(params = {}) {
  const out = {};
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined) continue;
    if (Array.isArray(value) && value.length === 0) continue;
    out[key] = value;
  }
  return out;
}

const get = (path) => (params) =>
  client.get(path, { params: cleanParams(params) }).then((res) => res.data);

export const getFilterOptions = () => client.get("/filters/options").then((res) => res.data);

// Bangun ulang cube atoti dari data terbaru di database (dipanggil setelah
// ada batch ETL baru yang di-load lewat CLI/ETL Monitor).
export const refreshCube = () => client.post("/cube/refresh").then((res) => res.data);

export const getKpi = get("/kpi");
export const getMonthlyTrend = get("/monthly-trend");
export const getChannelDistribution = get("/channel-distribution");
export const getCustomerSegment = get("/customer-segment");
export const getMerchantCategory = get("/merchant-category");
export const getTopMerchants = get("/top-merchants");
export const getGeographic = get("/geographic");
export const getCityRanking = get("/city-ranking");
export const getGenderDistribution = get("/gender-distribution");
export const getChannelByRegion = get("/channel-by-region");
export const getDailyTransaction = get("/daily-transaction");
export const getHeatmap = get("/heatmap");

// ETL Monitor
export const API_BASE_URL = "http://127.0.0.1:8000/api";
export const runEtl = (mode) =>
  client.post("/etl/run", null, { params: { mode } }).then((res) => res.data);
export const getEtlStatus = () => client.get("/etl/status").then((res) => res.data);
