import { getChannelDistribution } from "../../api";
import { useCubeQuery } from "../../hooks/useCubeQuery";
import ChartCard from "../ChartCard";
import DonutChart from "./DonutChart";

export default function ChannelDistributionChart() {
  const { data, loading } = useCubeQuery(getChannelDistribution);
  const rows = data || [];

  return (
    <ChartCard title="Distribusi Channel" subtitle="Volume transaksi per channel" height={300}>
      {!loading && rows.length === 0 ? (
        <div className="chart-empty">Tidak ada data</div>
      ) : (
        <DonutChart data={rows} nameKey="channel" showPercent />
      )}
    </ChartCard>
  );
}
