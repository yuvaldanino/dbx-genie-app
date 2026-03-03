/**
 * Leaflet map visualization — renders markers from lat/lon query results.
 */

import { useMemo } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// Fix default marker icons (Leaflet + bundler issue)
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

interface MapRendererProps {
  data: Record<string, string | number | null>[];
  latColumn: string;
  lonColumn: string;
  /** Column to use as marker popup label. */
  labelColumn?: string;
  columns: string[];
}

/** Auto-fit map bounds to all markers. */
function FitBounds({ points }: { points: [number, number][] }) {
  const map = useMap();
  useMemo(() => {
    if (points.length > 0) {
      const bounds = L.latLngBounds(points.map(([lat, lon]) => [lat, lon]));
      map.fitBounds(bounds, { padding: [30, 30], maxZoom: 12 });
    }
  }, [points, map]);
  return null;
}

export function MapRenderer({ data, latColumn, lonColumn, labelColumn, columns }: MapRendererProps) {
  const points = useMemo(() => {
    return data
      .map((row) => {
        const lat = Number(row[latColumn]);
        const lon = Number(row[lonColumn]);
        if (isNaN(lat) || isNaN(lon)) return null;
        return { lat, lon, row };
      })
      .filter(Boolean) as { lat: number; lon: number; row: Record<string, string | number | null> }[];
  }, [data, latColumn, lonColumn]);

  if (points.length === 0) {
    return <p className="text-sm text-muted-foreground p-4">No valid coordinates found.</p>;
  }

  const center: [number, number] = [
    points.reduce((s, p) => s + p.lat, 0) / points.length,
    points.reduce((s, p) => s + p.lon, 0) / points.length,
  ];

  // Columns to show in popup (exclude lat/lon)
  const popupCols = columns.filter((c) => c !== latColumn && c !== lonColumn).slice(0, 5);

  return (
    <div className="rounded-md overflow-hidden border" style={{ height: 360 }}>
      <MapContainer
        center={center}
        zoom={3}
        style={{ height: "100%", width: "100%" }}
        scrollWheelZoom
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitBounds points={points.map((p) => [p.lat, p.lon])} />
        {points.map((point, i) => (
          <Marker key={i} position={[point.lat, point.lon]}>
            <Popup>
              <div className="text-xs space-y-0.5">
                {labelColumn && point.row[labelColumn] && (
                  <p className="font-semibold">{String(point.row[labelColumn])}</p>
                )}
                {popupCols.map((col) => (
                  <p key={col}>
                    <span className="text-gray-500">{col}:</span> {String(point.row[col] ?? "—")}
                  </p>
                ))}
                <p className="text-gray-400">
                  {point.lat.toFixed(4)}, {point.lon.toFixed(4)}
                </p>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
