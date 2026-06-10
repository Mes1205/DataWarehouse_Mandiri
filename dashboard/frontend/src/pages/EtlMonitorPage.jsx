import { useEffect, useState } from "react";
import "../components/ChartCard.css";
import "../components/etl/Etl.css";
import { API_BASE_URL, runEtl } from "../api";
import EtlPipeline from "../components/etl/EtlPipeline";
import EtlLogConsole from "../components/etl/EtlLogConsole";

const STATUS_BADGE = {
  idle: { label: "Idle", className: "etl-badge-idle" },
  running: { label: "Berjalan", className: "etl-badge-running" },
  success: { label: "Selesai", className: "etl-badge-success" },
  error: { label: "Gagal", className: "etl-badge-error" },
};

const MODE_OPTIONS = [
  {
    value: "full",
    label: "Full Load",
    desc: "Truncate semua tabel lalu load ulang dimensi & fakta dari awal.",
  },
  {
    value: "incremental",
    label: "Incremental",
    desc: "Hanya insert baris dimensi/fakta baru tanpa truncate.",
  },
];

export default function EtlMonitorPage() {
  const [mode, setMode] = useState("incremental");
  const [state, setState] = useState({ status: "idle", mode: null, steps: [], logs: [] });
  const [message, setMessage] = useState(null);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    const source = new EventSource(`${API_BASE_URL}/etl/stream`);
    source.onmessage = (event) => {
      setState(JSON.parse(event.data));
    };
    return () => source.close();
  }, []);

  const isRunning = state.status === "running";
  const badge = STATUS_BADGE[state.status] || STATUS_BADGE.idle;

  const handleRun = async () => {
    setMessage(null);
    setStarting(true);
    try {
      const res = await runEtl(mode);
      if (!res.started) {
        setMessage(res.message || "ETL tidak bisa dijalankan");
      }
    } catch {
      setMessage("Gagal menghubungi backend ETL");
    } finally {
      setStarting(false);
    }
  };

  return (
    <div className="etl-page">
      <div className="chart-card">
        <div className="chart-card-title">ETL Pipeline Monitor</div>
        <div className="chart-card-subtitle">
          Visualisasi alur pipeline ETL (CSV → Star Schema PostgreSQL → Materialized View)
          tahap demi tahap. Ini adalah simulasi untuk memperjelas proses — tidak menjalankan
          ETL atau mengubah data sungguhan.
        </div>

        <div className="etl-controls">
          <div className="etl-mode-options">
            {MODE_OPTIONS.map((opt) => (
              <label
                key={opt.value}
                className={`etl-mode-option ${mode === opt.value ? "etl-mode-option-active" : ""}`}
              >
                <input
                  type="radio"
                  name="etl-mode"
                  value={opt.value}
                  checked={mode === opt.value}
                  onChange={() => setMode(opt.value)}
                  disabled={isRunning}
                />
                <div>
                  <div className="etl-mode-label">{opt.label}</div>
                  <div className="etl-mode-desc">{opt.desc}</div>
                </div>
              </label>
            ))}
          </div>

          <div className="etl-run-area">
            <span className={`etl-badge ${badge.className}`}>{badge.label}</span>
            <button className="etl-run-btn" onClick={handleRun} disabled={isRunning || starting}>
              {isRunning ? "Simulasi Berjalan..." : "Jalankan Simulasi"}
            </button>
          </div>
        </div>

        {message && <div className="etl-message">{message}</div>}
      </div>

      <div className="chart-card">
        <div className="chart-card-title">Alur Proses</div>
        <div className="chart-card-subtitle">
          {state.mode
            ? `Mode terakhir: ${state.mode === "full" ? "Full Load" : "Incremental"}`
            : "Belum ada proses yang dijalankan"}
        </div>
        <EtlPipeline steps={state.steps} />
      </div>

      <div className="chart-card">
        <div className="chart-card-title">Live Log (Simulasi)</div>
        <div className="chart-card-subtitle">
          Contoh output yang merepresentasikan proses ETL sesungguhnya (main.py)
        </div>
        <EtlLogConsole logs={state.logs} />
      </div>
    </div>
  );
}
