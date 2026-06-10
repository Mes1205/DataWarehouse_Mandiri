import { getGenderDistribution } from "../../api";
import { useCubeQuery } from "../../hooks/useCubeQuery";
import ChartCard from "../ChartCard";
import DonutChart from "./DonutChart";

const GENDER_LABELS = { L: "Laki-laki", P: "Perempuan", U: "Unknown" };

export default function GenderDistributionChart() {
  const { data, loading } = useCubeQuery(getGenderDistribution);
  const rows = (data || []).map((row) => ({
    ...row,
    jenis_kelamin: GENDER_LABELS[row.jenis_kelamin] || row.jenis_kelamin,
  }));

  return (
    <ChartCard title="Gender Distribution" subtitle="Volume transaksi per gender nasabah" height={300}>
      {!loading && rows.length === 0 ? (
        <div className="chart-empty">Tidak ada data</div>
      ) : (
        <DonutChart data={rows} nameKey="jenis_kelamin" showPercent />
      )}
    </ChartCard>
  );
}
