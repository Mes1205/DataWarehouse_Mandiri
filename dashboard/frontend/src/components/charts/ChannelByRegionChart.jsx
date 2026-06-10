import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getChannelByRegion } from "../../api";
import { useCubeQuery } from "../../hooks/useCubeQuery";
import ChartCard from "../ChartCard";
import { CHART_COLORS, formatNumber } from "../../utils/format";

export default function ChannelByRegionChart() {
  const { data, loading } = useCubeQuery(getChannelByRegion);
  const rows = data?.data || [];
  const channels = data?.channels || [];

  return (
    <ChartCard
      title="Channel Usage by Region"
      subtitle="Jumlah transaksi per channel di tiap kota"
      height={320}
    >
      {!loading && rows.length === 0 ? (
        <div className="chart-empty">Tidak ada data</div>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="var(--border-color)" strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="kota" stroke="var(--text-secondary)" fontSize={11} tickLine={false} />
            <YAxis
              stroke="var(--text-secondary)"
              fontSize={11}
              tickLine={false}
              tickFormatter={formatNumber}
              width={50}
            />
            <Tooltip
              contentStyle={{
                background: "var(--bg-panel-hover)",
                border: "1px solid var(--border-color)",
                borderRadius: 8,
                fontSize: 12,
              }}
              labelStyle={{ color: "var(--text-primary)" }}
              formatter={(value, name, item) => {
                const total = channels.reduce((sum, ch) => sum + (item.payload[ch] || 0), 0);
                const pct = total ? ((value / total) * 100).toFixed(1) : 0;
                return [`${formatNumber(value)} (${pct}%)`, name];
              }}
            />
            <Legend wrapperStyle={{ fontSize: 12, color: "var(--text-secondary)" }} />
            {channels.map((ch, idx) => (
              <Bar
                key={ch}
                dataKey={ch}
                stackId="channel"
                fill={CHART_COLORS[idx % CHART_COLORS.length]}
                radius={idx === channels.length - 1 ? [4, 4, 0, 0] : 0}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      )}
    </ChartCard>
  );
}
