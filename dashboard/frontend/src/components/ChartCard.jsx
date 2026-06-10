import { motion } from "framer-motion";
import "./ChartCard.css";

export default function ChartCard({ title, subtitle, height = 300, className = "", children }) {
  return (
    <motion.div
      className={`chart-card ${className}`}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="chart-card-title">{title}</div>
      {subtitle && <div className="chart-card-subtitle">{subtitle}</div>}
      <div className="chart-card-body" style={{ height }}>
        {children}
      </div>
    </motion.div>
  );
}
