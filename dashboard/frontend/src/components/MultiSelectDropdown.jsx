import { useEffect, useRef, useState } from "react";
import "./MultiSelectDropdown.css";

export default function MultiSelectDropdown({ label, options, value, onChange, placeholder = "Semua" }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);
  const opts = options || [];
  const vals = value || [];

  useEffect(() => {
    function handleClickOutside(e) {
      if (rootRef.current && !rootRef.current.contains(e.target)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const toggleOption = (opt) => {
    if (vals.includes(opt)) {
      onChange(vals.filter((v) => v !== opt));
    } else {
      onChange([...vals, opt]);
    }
  };

  let summary = placeholder;
  if (vals.length === 1) summary = vals[0];
  else if (vals.length > 1) summary = `${vals.length} dipilih`;

  return (
    <div className="msd" ref={rootRef}>
      <label>{label}</label>
      <button
        type="button"
        className={`msd-trigger ${vals.length ? "msd-trigger-active" : ""}`}
        onClick={() => setOpen((o) => !o)}
      >
        <span className="msd-summary">{summary}</span>
        <span className={`msd-arrow ${open ? "msd-arrow-open" : ""}`}>▾</span>
      </button>
      {open && (
        <div className="msd-panel">
          <div className="msd-panel-actions">
            <button type="button" onClick={() => onChange([...opts])}>
              Pilih Semua
            </button>
            <button type="button" onClick={() => onChange([])}>
              Hapus
            </button>
          </div>
          <div className="msd-options">
            {opts.length === 0 && <div className="msd-empty">Tidak ada opsi</div>}
            {opts.map((opt) => (
              <label key={opt} className="msd-option">
                <input
                  type="checkbox"
                  checked={vals.includes(opt)}
                  onChange={() => toggleOption(opt)}
                />
                <span>{opt}</span>
              </label>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
