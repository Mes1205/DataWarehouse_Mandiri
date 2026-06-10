import { useFilters } from "../context/FilterContext";
import MultiSelectDropdown from "./MultiSelectDropdown";
import "./FilterBar.css";

export default function FilterBar() {
  const {
    options,
    loadingOptions,
    filters,
    setFilter,
    resetFilters,
    hasActiveFilters,
    isRefreshing,
    refreshAll,
  } = useFilters();

  if (loadingOptions || !options) {
    return <div className="filter-bar">Memuat filter...</div>;
  }

  return (
    <div className="filter-bar">
      <div className="filter-group">
        <div className="filter-group-label">Periode Waktu</div>
        <div className="filter-row filter-row-period">
          <MultiSelectDropdown
            label="Tahun"
            options={options.tahun.map(String)}
            value={filters.tahun.map(String)}
            onChange={(v) => setFilter("tahun", v.map(Number))}
          />
          <MultiSelectDropdown
            label="Quarter"
            options={options.quarter}
            value={filters.quarter}
            onChange={(v) => setFilter("quarter", v)}
          />
          <MultiSelectDropdown
            label="Bulan"
            options={options.bulan}
            value={filters.bulan}
            onChange={(v) => setFilter("bulan", v)}
          />
          <div className="filter-field">
            <label>Dari Tanggal</label>
            <input
              type="date"
              min={options.min_date}
              max={options.max_date}
              value={filters.start_date || ""}
              onChange={(e) => setFilter("start_date", e.target.value || null)}
            />
          </div>
          <div className="filter-field">
            <label>Sampai Tanggal</label>
            <input
              type="date"
              min={options.min_date}
              max={options.max_date}
              value={filters.end_date || ""}
              onChange={(e) => setFilter("end_date", e.target.value || null)}
            />
          </div>
        </div>
      </div>

      <div className="filter-group">
        <div className="filter-group-label">Dimensi Analisis</div>
        <div className="filter-row filter-row-dimension">
          <MultiSelectDropdown
            label="Channel"
            options={options.channel}
            value={filters.channel}
            onChange={(v) => setFilter("channel", v)}
          />
          <MultiSelectDropdown
            label="Segmen Nasabah"
            options={options.segmen}
            value={filters.segmen}
            onChange={(v) => setFilter("segmen", v)}
          />
          <MultiSelectDropdown
            label="Kategori Merchant"
            options={options.kategori}
            value={filters.kategori}
            onChange={(v) => setFilter("kategori", v)}
          />
          <MultiSelectDropdown
            label="Provinsi"
            options={options.provinsi}
            value={filters.provinsi}
            onChange={(v) => setFilter("provinsi", v)}
          />
          <MultiSelectDropdown
            label="Kota"
            options={options.kota}
            value={filters.kota}
            onChange={(v) => setFilter("kota", v)}
          />
          <div className="filter-field filter-checkbox-field">
            <label>&nbsp;</label>
            <label className="filter-checkbox">
              <input
                type="checkbox"
                checked={filters.include_unknown}
                onChange={(e) => setFilter("include_unknown", e.target.checked)}
              />
              <span>Tampilkan data "Unknown"</span>
            </label>
          </div>
          <div className="filter-field filter-actions">
            <label>&nbsp;</label>
            <div className="filter-actions-buttons">
              <button
                className="filter-refresh"
                onClick={refreshAll}
                disabled={isRefreshing}
                title="Muat ulang cube dari data terbaru di database"
              >
                {isRefreshing ? "Memuat..." : "Refresh Data"}
              </button>
              <button className="filter-reset" onClick={resetFilters} disabled={!hasActiveFilters}>
                Reset Filter
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
