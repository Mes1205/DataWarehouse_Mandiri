import { Bar, BarChart, CartesianGrid, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getCityRanking } from "../../api";
import { useCubeQuery } from "../../hooks/useCubeQuery";
import ChartCard from "../ChartCard";
import { formatCompactNumber, formatCurrencyTooltip } from "../../utils/format";

export default function CityRankingChart() {
  const { data, loading } = useCubeQuery(getCityRanking);
  const rows = data || [];

  return (
    <ChartCard title="City Ranking" subtitle="Volume transaksi per kota" height={300}>
      {!loading && rows.length === 0 ? (
        <div className="chart-empty">Tidak ada data</div>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={rows}
            layout="vertical"
            margin={{ top: 4, right: 40, left: 8, bottom: 0 }}
          >
            <CartesianGrid stroke="var(--border-color)" strokeDasharray="3 3" horizontal={false} />
            <XAxis
              type="number"
              stroke="var(--text-secondary)"
              fontSize={11}
              tickLine={false}
              tickFormatter={formatCompactNumber}
            />
            <YAxis
              type="category"
              dataKey="kota"
              stroke="var(--text-secondary)"
              fontSize={11}
              tickLine={false}
              width={90}
            />
            <Tooltip
              contentStyle={{
                background: "var(--bg-panel-hover)",
                border: "1px solid var(--border-color)",
                borderRadius: 8,
                fontSize: 12,
              }}
              formatter={(value) => [formatCurrencyTooltip(value), "Volume Transaksi"]}
            />
            <Bar dataKey="total_volume_transaksi" fill="var(--chart-2)" radius={[0, 4, 4, 0]}>
              <LabelList
                dataKey="total_volume_transaksi"
                position="right"
                formatter={formatCompactNumber}
                fill="var(--text-secondary)"
                fontSize={11}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </ChartCard>
  );
}
