import { useState } from "react";
import { getTopMerchants } from "../../api";
import { useCubeQuery } from "../../hooks/useCubeQuery";
import ChartCard from "../ChartCard";
import { formatCurrencyTooltip, formatNumber } from "../../utils/format";
import "./TopMerchantsTable.css";

const COLUMNS = [
  { key: "rank", label: "No", numeric: true, sortable: false },
  { key: "nama_merchant", label: "Merchant" },
  { key: "kategori", label: "Kategori" },
  { key: "total_volume_transaksi", label: "Volume Transaksi", numeric: true },
  { key: "jumlah_transaksi", label: "Frekuensi", numeric: true },
];

export default function TopMerchantsTable() {
  const { data, loading } = useCubeQuery(getTopMerchants, { limit: 10 });
  const [sort, setSort] = useState({ key: "total_volume_transaksi", dir: "desc" });

  const rows = [...(data || [])].sort((a, b) => {
    const { key, dir } = sort;
    const mult = dir === "asc" ? 1 : -1;
    if (typeof a[key] === "string") return a[key].localeCompare(b[key]) * mult;
    return (a[key] - b[key]) * mult;
  });
  const maxVolume = rows.reduce((max, r) => Math.max(max, r.total_volume_transaksi), 0);

  const toggleSort = (key) => {
    setSort((prev) =>
      prev.key === key ? { key, dir: prev.dir === "asc" ? "desc" : "asc" } : { key, dir: "desc" }
    );
  };

  return (
    <ChartCard
      title="Top Merchant Analysis"
      subtitle="Tabel interaktif - klik header untuk mengurutkan"
      height={320}
    >
      {!loading && rows.length === 0 ? (
        <div className="chart-empty">Tidak ada data</div>
      ) : (
        <div className="table-scroll">
          <table className="top-merchants-table">
            <thead>
              <tr>
                {COLUMNS.map((col) => (
                  <th
                    key={col.key}
                    className={[col.numeric && "numeric", col.sortable !== false && "sortable"]
                      .filter(Boolean)
                      .join(" ")}
                    onClick={col.sortable === false ? undefined : () => toggleSort(col.key)}
                  >
                    {col.label}
                    {sort.key === col.key ? (sort.dir === "asc" ? " ▲" : " ▼") : ""}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, idx) => (
                <tr key={`${row.kategori}-${row.nama_merchant}`}>
                  <td className="numeric">{idx + 1}</td>
                  <td>
                    {row.nama_merchant}
                    <div className="rank-bar-track">
                      <div
                        className="rank-bar-fill"
                        style={{
                          width: `${maxVolume ? (row.total_volume_transaksi / maxVolume) * 100 : 0}%`,
                        }}
                      />
                    </div>
                  </td>
                  <td>{row.kategori}</td>
                  <td className="numeric">{formatCurrencyTooltip(row.total_volume_transaksi)}</td>
                  <td className="numeric">{formatNumber(row.jumlah_transaksi)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </ChartCard>
  );
}
