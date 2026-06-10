import { useEffect, useRef, useState } from "react";
import { motion, useMotionValue, useSpring } from "framer-motion";
import "./KpiCard.css";

function formatNumber(value, format) {
  if (value === null || value === undefined || Number.isNaN(value)) return "-";
  if (format === "currency") {
    return new Intl.NumberFormat("id-ID", {
      style: "currency",
      currency: "IDR",
      maximumFractionDigits: 0,
    }).format(value);
  }
  if (format === "currency-compact-billion") {
    const billions = value / 1_000_000_000;
    return `Rp ${new Intl.NumberFormat("id-ID", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(billions)} M`;
  }
  if (format === "currency-compact-million") {
    const millions = value / 1_000_000;
    return `Rp ${new Intl.NumberFormat("id-ID", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(millions)} Jt`;
  }
  return new Intl.NumberFormat("id-ID", { maximumFractionDigits: 0 }).format(value);
}

// Animasi count-up halus dari 0 -> value menggunakan spring framer-motion.
function AnimatedNumber({ value, format }) {
  const motionValue = useMotionValue(0);
  const spring = useSpring(motionValue, { stiffness: 80, damping: 22 });
  const [display, setDisplay] = useState(0);
  const firstRun = useRef(true);

  useEffect(() => {
    if (value === null || value === undefined) return;
    motionValue.set(firstRun.current ? 0 : motionValue.get());
    spring.set(value);
    firstRun.current = false;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  useEffect(() => {
    const unsubscribe = spring.on("change", (latest) => setDisplay(latest));
    return unsubscribe;
  }, [spring]);

  return <span>{formatNumber(display, format)}</span>;
}

export default function KpiCard({ label, value, format, trend, loading, expandable }) {
  const [expanded, setExpanded] = useState(false);

  const trendClass =
    trend === null || trend === undefined
      ? "neutral"
      : trend > 0
      ? "positive"
      : trend < 0
      ? "negative"
      : "neutral";

  const trendArrow = trend > 0 ? "▲" : trend < 0 ? "▼" : "■";

  const displayFormat = expandable ? (expanded ? "currency" : format) : format;

  return (
    <motion.div
      className={`kpi-card ${expandable ? "kpi-card-clickable" : ""}`}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      onClick={expandable ? () => setExpanded((e) => !e) : undefined}
      role={expandable ? "button" : undefined}
      tabIndex={expandable ? 0 : undefined}
    >
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">
        {loading || value === null || value === undefined ? (
          "-"
        ) : (
          <AnimatedNumber value={value} format={displayFormat} />
        )}
      </div>
      {trend !== null && trend !== undefined && (
        <div className={`kpi-trend ${trendClass}`}>
          <span>{trendArrow}</span>
          <span>{Math.abs(trend)}% MoM</span>
        </div>
      )}
      {expandable && !loading && value !== null && value !== undefined && (
        <div className="kpi-hint">
          {expanded ? "Klik untuk ringkas" : "Klik untuk lihat nominal penuh"}
        </div>
      )}
    </motion.div>
  );
}
