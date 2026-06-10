import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getMonthlyTrend } from "../../api";
import { useCubeQuery } from "../../hooks/useCubeQuery";
import ChartCard from "../ChartCard";
import { formatCompactNumber, formatCurrencyTooltip } from "../../utils/format";

export default function MonthlyTrendChart() {
  const { data, loading } = useCubeQuery(getMonthlyTrend);
  const rows = data?.data || [];
  const isDaily = data?.granularity === "day";

  return (
    <ChartCard
      title="Tren Transaksi Bulanan"
      subtitle={
        isDaily
          ? "Drill-down: tren harian untuk bulan terpilih"
          : "Roll-up: tren bulanan (pilih 1 tahun & 1 bulan untuk drill-down ke harian)"
      }
      height={320}
    >
      {!loading && rows.length === 0 ? (
        <div className="chart-empty">Tidak ada data</div>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="var(--border-color)" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="label"
              stroke="var(--text-secondary)"
              fontSize={11}
              tickLine={false}
              interval={isDaily ? 2 : 0}
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
              labelStyle={{ color: "var(--text-primary)" }}
              formatter={(value, name) =>
                name === "total_volume_transaksi"
                  ? [formatCurrencyTooltip(value), "Volume Transaksi"]
                  : [value, "Jumlah Transaksi"]
              }
            />
            <Line
              type="monotone"
              dataKey="total_volume_transaksi"
              stroke="var(--chart-1)"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
              isAnimationActive={true}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </ChartCard>
  );
}
