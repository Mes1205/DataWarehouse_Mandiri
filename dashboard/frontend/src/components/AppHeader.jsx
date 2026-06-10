import { NavLink } from "react-router-dom";

export default function AppHeader() {
  return (
    <header className="app-header">
      <div className="app-header-brand">
        <div className="brand-mark">M</div>
        <div>
          <h1>
            Dashboard Transaksi Digital <span className="brand-accent">Bank Mandiri</span>
          </h1>
          <div className="subtitle">
            Analitik transaksi digital real-time berbasis OLAP Cube (Atoti)
          </div>
        </div>
      </div>

      <div className="app-header-right">
        <nav className="app-nav">
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
            Dashboard
          </NavLink>
          <NavLink to="/etl" className={({ isActive }) => (isActive ? "active" : "")}>
            ETL Monitor
          </NavLink>
        </nav>
        <span className="badge">
          <span className="badge-dot" />
          Live OLAP
        </span>
      </div>
    </header>
  );
}
