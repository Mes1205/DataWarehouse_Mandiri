import { BrowserRouter, Route, Routes } from "react-router-dom";
import "./App.css";
import AppHeader from "./components/AppHeader";
import DashboardPage from "./pages/DashboardPage";
import EtlMonitorPage from "./pages/EtlMonitorPage";

function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <AppHeader />
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/etl" element={<EtlMonitorPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
