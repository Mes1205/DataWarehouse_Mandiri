import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getDailyTransaction } from "../../api";
import { useCubeQuery } from "../../hooks/useCubeQuery";
import ChartCard from "../ChartCard";
import { formatNumber } from "../../utils/format";

const DAY_SHORT = {
  Monday: "Sen",
  Tuesday: "Sel",
  Wednesday: "Rab",
  Thursday: "Kam",
  Friday: "Jum",
  Saturday: "Sab",
  Sunday: "Min",
};

export default function DailyTransactionChart() {
  const { data, loading } = useCubeQuery(getDailyTransaction);
  const rows = (data || []).map((row) => ({ ...row, hari_label: DAY_SHORT[row.hari] || row.hari }));
  const peakIdx = rows.reduce(
    (best, row, idx) => (row.jumlah_transaksi > (rows[best]?.jumlah_transaksi ?? -1) ? idx : best),
    0
  );

  return (
    <ChartCard
      title="Daily Transaction Analysis"
      subtitle="Jumlah transaksi per hari (peak day disorot)"
      height={300}
    >
      {!loading && rows.length === 0 ? (
        <div className="chart-empty">Tidak ada data</div>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="var(--border-color)" strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="hari_label" stroke="var(--text-secondary)" fontSize={11} tickLine={false} />
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
              itemStyle={{ color: "var(--accent)" }}
              cursor={{ fill: "var(--accent-soft)" }}
              formatter={(value) => [formatNumber(value), "Jumlah Transaksi"]}
            />
            <Bar dataKey="jumlah_transaksi" radius={[4, 4, 0, 0]}>
              {rows.map((_, idx) => (
                <Cell key={idx} fill={idx === peakIdx ? "var(--accent)" : "#2d3f66"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </ChartCard>
  );
}
