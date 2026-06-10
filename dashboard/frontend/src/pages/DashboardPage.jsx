import "../components/ChartCard.css";
import { FilterProvider } from "../context/FilterContext";
import FilterBar from "../components/FilterBar";
import KpiCards from "../components/KpiCards";
import MonthlyTrendChart from "../components/charts/MonthlyTrendChart";
import ChannelDistributionChart from "../components/charts/ChannelDistributionChart";
import CustomerSegmentChart from "../components/charts/CustomerSegmentChart";
import GenderDistributionChart from "../components/charts/GenderDistributionChart";
import MerchantCategoryChart from "../components/charts/MerchantCategoryChart";
import TopMerchantsTable from "../components/charts/TopMerchantsTable";
import GeographicMap from "../components/charts/GeographicMap";
import CityRankingChart from "../components/charts/CityRankingChart";
import ChannelByRegionChart from "../components/charts/ChannelByRegionChart";
import DailyTransactionChart from "../components/charts/DailyTransactionChart";
import HeatmapChart from "../components/charts/HeatmapChart";

export default function DashboardPage() {
  return (
    <FilterProvider>
      <FilterBar />
      <KpiCards />

      <div className="dashboard-grid">
        <div className="span-8">
          <MonthlyTrendChart />
        </div>
        <div className="span-4">
          <ChannelDistributionChart />
        </div>

        <div className="span-4">
          <CustomerSegmentChart />
        </div>
        <div className="span-4">
          <GenderDistributionChart />
        </div>
        <div className="span-4">
          <MerchantCategoryChart />
        </div>

        <div className="span-6">
          <GeographicMap />
        </div>
        <div className="span-6">
          <CityRankingChart />
        </div>

        <div className="span-12">
          <TopMerchantsTable />
        </div>

        <div className="span-6">
          <ChannelByRegionChart />
        </div>
        <div className="span-6">
          <DailyTransactionChart />
        </div>

        <div className="span-12">
          <HeatmapChart />
        </div>
      </div>
    </FilterProvider>
  );
}
