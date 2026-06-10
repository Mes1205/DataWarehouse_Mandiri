import { useEffect, useState } from "react";
import { useFilters } from "../context/FilterContext";

// Re-fetch data dari backend (yang query ke Atoti cube) setiap kali filter
// global berubah. extraParams (opsional) untuk param tambahan per-chart (mis. limit).
export function useCubeQuery(fetchFn, extraParams = {}) {
  const { filters, refreshKey } = useFilters();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const extraKey = JSON.stringify(extraParams);

  useEffect(() => {
    let cancelled = false;
    const loadingTimer = setTimeout(() => {
      if (!cancelled) setLoading(true);
    }, 0);
    fetchFn({ ...filters, ...JSON.parse(extraKey) })
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .finally(() => {
        if (!cancelled) {
          clearTimeout(loadingTimer);
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
      clearTimeout(loadingTimer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(filters), extraKey, refreshKey]);

  return { data, loading };
}
