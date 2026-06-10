import { useEffect, useRef } from "react";
import "./Etl.css";

export default function EtlLogConsole({ logs }) {
  const containerRef = useRef(null);

  useEffect(() => {
    const el = containerRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [logs]);

  return (
    <div className="etl-log-console" ref={containerRef}>
      {!logs || logs.length === 0 ? (
        <div className="etl-log-empty">Belum ada log. Jalankan pipeline untuk melihat output secara live.</div>
      ) : (
        logs.map((line, idx) => (
          <div key={idx} className="etl-log-line">
            {line}
          </div>
        ))
      )}
    </div>
  );
}
