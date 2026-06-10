import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { CHART_COLORS, formatCurrencyTooltip, formatNumber } from "../../utils/format";

// Label persentase ditempatkan di tengah tiap slice; slice yang terlalu kecil disembunyikan
// labelnya supaya tidak bertumpuk.
function renderPercentLabel({ cx, cy, midAngle, innerRadius, outerRadius, percent }) {
  if (percent < 0.05) return null;
  const RADIAN = Math.PI / 180;
  const radius = innerRadius + (outerRadius - innerRadius) * 0.55;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);
  return (
    <text
      x={x}
      y={y}
      fill="#0b1220"
      textAnchor="middle"
      dominantBaseline="central"
      fontSize={12}
      fontWeight={700}
    >
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  );
}

// Donut generik dipakai untuk Channel Distribution, Customer Segment, Gender Distribution.
export default function DonutChart({ data, nameKey, valueKey = "total_volume_transaksi", showPercent = false }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart>
        <Pie
          data={data}
          dataKey={valueKey}
          nameKey={nameKey}
          innerRadius="55%"
          outerRadius="80%"
          paddingAngle={2}
          isAnimationActive={true}
          label={showPercent ? renderPercentLabel : false}
          labelLine={false}
        >
          {data.map((_, idx) => (
            <Cell key={idx} fill={CHART_COLORS[idx % CHART_COLORS.length]} stroke="none" />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            background: "var(--bg-panel-hover)",
            border: "1px solid var(--border-color)",
            borderRadius: 8,
            fontSize: 12,
          }}
          formatter={(value, _name, item) => [
            `${formatCurrencyTooltip(value)} (${formatNumber(item.payload.jumlah_transaksi)} trx)`,
            item.payload[nameKey],
          ]}
        />
        <Legend
          wrapperStyle={{ fontSize: 12, color: "var(--text-secondary)" }}
          iconType="circle"
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
