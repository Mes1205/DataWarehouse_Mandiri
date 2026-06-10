import { getCustomerSegment } from "../../api";
import { useCubeQuery } from "../../hooks/useCubeQuery";
import ChartCard from "../ChartCard";
import DonutChart from "./DonutChart";

export default function CustomerSegmentChart() {
  const { data, loading } = useCubeQuery(getCustomerSegment);
  const rows = data || [];

  return (
    <ChartCard
      title="Customer Segment Contribution"
      subtitle="Volume transaksi per segmen nasabah"
      height={300}
    >
      {!loading && rows.length === 0 ? (
        <div className="chart-empty">Tidak ada data</div>
      ) : (
        <DonutChart data={rows} nameKey="segmen" showPercent />
      )}
    </ChartCard>
  );
}
