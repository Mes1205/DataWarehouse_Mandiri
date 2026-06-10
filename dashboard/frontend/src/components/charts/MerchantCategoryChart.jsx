import { Bar, BarChart, CartesianGrid, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getMerchantCategory } from "../../api";
import { useCubeQuery } from "../../hooks/useCubeQuery";
import ChartCard from "../ChartCard";
import { formatCompactNumber, formatCurrencyTooltip } from "../../utils/format";

export default function MerchantCategoryChart() {
  const { data, loading } = useCubeQuery(getMerchantCategory);
  const rows = data || [];

  return (
    <ChartCard
      title="Merchant Category Ranking"
      subtitle="Volume transaksi per kategori merchant"
      height={300}
    >
      {!loading && rows.length === 0 ? (
        <div className="chart-empty">Tidak ada data</div>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ top: 20, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="var(--border-color)" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="kategori"
              stroke="var(--text-secondary)"
              fontSize={11}
              tickLine={false}
              interval={0}
              angle={-20}
              textAnchor="end"
              height={50}
            />
            <YAxis
              stroke="var(--text-secondary)"
              fontSize={11}
              tickLine={false}
              tickFormatter={formatCompactNumber}
              width={56}
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
            <Bar dataKey="total_volume_transaksi" fill="var(--chart-2)" radius={[4, 4, 0, 0]}>
              <LabelList
                dataKey="total_volume_transaksi"
                position="top"
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
