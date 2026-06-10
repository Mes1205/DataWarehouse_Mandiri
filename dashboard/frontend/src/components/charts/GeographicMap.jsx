import "leaflet/dist/leaflet.css";
import { CircleMarker, MapContainer, Popup, TileLayer } from "react-leaflet";
import { getGeographic } from "../../api";
import { useCubeQuery } from "../../hooks/useCubeQuery";
import ChartCard from "../ChartCard";
import { formatCurrencyTooltip, formatNumber } from "../../utils/format";

const INDONESIA_CENTER = [-2.5489, 118.0149];

export default function GeographicMap() {
  const { data, loading } = useCubeQuery(getGeographic);
  const rows = data || [];
  const maxVolume = rows.reduce((max, r) => Math.max(max, r.total_volume_transaksi), 0);

  return (
    <ChartCard
      title="Geographic Transaction Analysis"
      subtitle="Sebaran volume transaksi per kota (ukuran lingkaran = volume)"
      height={360}
    >
      {!loading && rows.length === 0 ? (
        <div className="chart-empty">Tidak ada data</div>
      ) : (
        <MapContainer
          center={INDONESIA_CENTER}
          zoom={5}
          style={{ height: "100%", width: "100%", borderRadius: 8 }}
          scrollWheelZoom={false}
        >
          <TileLayer
            attribution='&copy; OpenStreetMap contributors'
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          />
          {rows.map((row) => (
            <CircleMarker
              key={`${row.provinsi}-${row.kota}`}
              center={[row.lat, row.lon]}
              radius={maxVolume ? 6 + (row.total_volume_transaksi / maxVolume) * 24 : 6}
              pathOptions={{ color: "#38bdf8", fillColor: "#4f8cf7", fillOpacity: 0.45 }}
            >
              <Popup>
                <strong>{row.kota}</strong> ({row.provinsi})
                <br />
                Volume: {formatCurrencyTooltip(row.total_volume_transaksi)}
                <br />
                Frekuensi: {formatNumber(row.jumlah_transaksi)} transaksi
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>
      )}
    </ChartCard>
  );
}
