import { getHeatmap } from "../../api";
import { useCubeQuery } from "../../hooks/useCubeQuery";
import ChartCard from "../ChartCard";
import "./HeatmapChart.css";

const DAY_SHORT = { Monday: "Sen", Tuesday: "Sel", Wednesday: "Rab", Thursday: "Kam", Friday: "Jum", Saturday: "Sab", Sunday: "Min" };
const MONTH_SHORT = {
  January: "Jan", February: "Feb", March: "Mar", April: "Apr", May: "Mei", June: "Jun",
  July: "Jul", August: "Agu", September: "Sep", October: "Okt", November: "Nov", December: "Des",
};

function cellColor(value, max) {
  if (!max) return "rgba(79, 140, 247, 0.05)";
  const ratio = value / max;
  return `rgba(79, 140, 247, ${0.08 + ratio * 0.82})`;
}

export default function HeatmapChart() {
  const { data, loading } = useCubeQuery(getHeatmap);
  const bulan = data?.bulan || [];
  const hari = data?.hari || [];
  const rows = data?.data || [];

  const max = rows.reduce((m, r) => Math.max(m, r.jumlah_transaksi), 0);
  const lookup = {};
  rows.forEach((r) => {
    lookup[`${r.bulan}-${r.hari}`] = r.jumlah_transaksi;
  });

  return (
    <ChartCard
      title="Heatmap Transaksi (Bulan x Hari)"
      subtitle="Intensitas jumlah transaksi per bulan & hari"
      height={340}
    >
      {!loading && bulan.length === 0 ? (
        <div className="chart-empty">Tidak ada data</div>
      ) : (
        <div className="heatmap">
          <div className="heatmap-row header">
            <div className="row-label" />
            {hari.map((h) => (
              <div className="heatmap-cell header-cell" key={h}>
                {DAY_SHORT[h] || h}
              </div>
            ))}
          </div>
          {bulan.map((b) => (
            <div className="heatmap-row" key={b}>
              <div className="row-label">{MONTH_SHORT[b] || b}</div>
              {hari.map((h) => {
                const value = lookup[`${b}-${h}`] || 0;
                return (
                  <div
                    className="heatmap-cell"
                    key={h}
                    style={{ background: cellColor(value, max) }}
                    title={`${b} - ${h}: ${value} transaksi`}
                  >
                    {value}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      )}
    </ChartCard>
  );
}
