import "./Etl.css";

const STATUS_LABEL = {
  pending: "Menunggu",
  running: "Berjalan",
  success: "Selesai",
  error: "Gagal",
};

const STATUS_ICON = {
  pending: "○",
  running: "◐",
  success: "✓",
  error: "✕",
};

export default function EtlPipeline({ steps }) {
  if (!steps || steps.length === 0) {
    return (
      <div className="etl-pipeline etl-pipeline-empty">
        Pilih mode pipeline lalu klik "Jalankan ETL" untuk melihat alur prosesnya di sini.
      </div>
    );
  }

  // Kelompokkan step berurutan berdasarkan field "group" tanpa mengubah urutan asli.
  const groups = [];
  for (const step of steps) {
    const last = groups[groups.length - 1];
    if (last && last.name === step.group) {
      last.items.push(step);
    } else {
      groups.push({ name: step.group, items: [step] });
    }
  }

  return (
    <div className="etl-pipeline">
      {groups.map((group) => (
        <div className="etl-pipeline-group" key={group.name}>
          <div className="etl-pipeline-group-title">{group.name}</div>
          <div className="etl-pipeline-group-items">
            {group.items.map((step) => (
              <div className={`etl-step etl-step-${step.status}`} key={step.key}>
                <div className="etl-step-icon">{STATUS_ICON[step.status]}</div>
                <div className="etl-step-body">
                  <div className="etl-step-label">{step.label}</div>
                  {step.desc && <div className="etl-step-desc">{step.desc}</div>}
                </div>
                <div className="etl-step-status">{STATUS_LABEL[step.status]}</div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
