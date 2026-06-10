import { getKpi } from "../api";
import { useCubeQuery } from "../hooks/useCubeQuery";
import KpiCard from "./KpiCard";
import "./KpiCard.css";

export default function KpiCards() {
  const { data, loading } = useCubeQuery(getKpi);
  const trend = data?.trend;

  return (
    <div className="kpi-grid">
      <KpiCard
        label="Total Volume Transaksi"
        value={data?.total_volume_transaksi}
        format="currency-compact-billion"
        expandable
        trend={trend?.total_volume_transaksi}
        loading={loading}
      />
      <KpiCard
        label="Total Frekuensi Transaksi"
        value={data?.total_frekuensi_transaksi}
        format="number"
        trend={trend?.total_frekuensi_transaksi}
        loading={loading}
      />
      <KpiCard
        label="Total Revenue Transaksi"
        value={data?.total_revenue_transaksi}
        format="currency-compact-million"
        expandable
        trend={trend?.total_revenue_transaksi}
        loading={loading}
      />
      <KpiCard
        label="Average Nominal Transaksi"
        value={data?.avg_nominal_transaksi}
        format="currency-compact-million"
        expandable
        trend={trend?.avg_nominal_transaksi}
        loading={loading}
      />
    </div>
  );
}
