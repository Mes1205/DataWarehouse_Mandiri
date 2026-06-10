import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { getFilterOptions, refreshCube } from "../api";

const FilterContext = createContext(null);

const EMPTY_FILTERS = {
  tahun: [],
  quarter: [],
  bulan: [],
  channel: [],
  segmen: [],
  kategori: [],
  provinsi: [],
  kota: [],
  start_date: null,
  end_date: null,
  include_unknown: false,
};

export function FilterProvider({ children }) {
  const [options, setOptions] = useState(null);
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);

  useEffect(() => {
    getFilterOptions()
      .then(setOptions)
      .finally(() => setLoadingOptions(false));
  }, []);

  // Bangun ulang cube atoti dari data terbaru di DB, lalu refresh opsi filter
  // (tahun/bulan/kota dsb) dan trigger semua chart untuk fetch ulang.
  const refreshAll = async () => {
    setIsRefreshing(true);
    try {
      await refreshCube();
      const newOptions = await getFilterOptions();
      setOptions(newOptions);
      setRefreshKey((k) => k + 1);
    } finally {
      setIsRefreshing(false);
    }
  };

  const setFilter = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const resetFilters = () => setFilters(EMPTY_FILTERS);

  const hasActiveFilters = useMemo(
    () =>
      Object.values(filters).some((value) =>
        Array.isArray(value) ? value.length > 0 : Boolean(value)
      ),
    [filters]
  );

  const value = {
    options,
    loadingOptions,
    filters,
    setFilter,
    resetFilters,
    hasActiveFilters,
    refreshKey,
    isRefreshing,
    refreshAll,
  };

  return <FilterContext.Provider value={value}>{children}</FilterContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useFilters() {
  const ctx = useContext(FilterContext);
  if (!ctx) throw new Error("useFilters must be used within FilterProvider");
  return ctx;
}
