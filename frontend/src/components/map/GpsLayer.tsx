import React from 'react';
import { CircleMarker, Polyline, Popup, Tooltip } from 'react-leaflet';
import { GpsPoint } from '../../types/api';
import { toLatLngTuple } from '../../utils/geoUtils';

interface GpsLayerProps {
  points?: GpsPoint[];
  showObservations: boolean;
  showTrajectory: boolean;
}

export const GpsLayer: React.FC<GpsLayerProps> = ({
  points,
  showObservations,
  showTrajectory,
}) => {
  if (!points || points.length === 0) return null;

  // Extract valid coordinates for polyline
  const polylineCoords: [number, number][] = [];
  const validPoints: { point: GpsPoint; coord: [number, number]; index: number }[] = [];

  points.forEach((p, idx) => {
    const latLng = toLatLngTuple(p);
    if (latLng) {
      polylineCoords.push(latLng);
      validPoints.push({ point: p, coord: latLng, index: idx });
    }
  });

  return (
    <>
      {/* GPS Trajectory Polyline */}
      {showTrajectory && polylineCoords.length > 1 && (
        <Polyline
          positions={polylineCoords}
          pathOptions={{
            color: '#06b6d4', // cyan-500
            weight: 2,
            opacity: 0.65,
            dashArray: '5, 5',
          }}
        >
          <Tooltip sticky>
            <span className="font-mono text-xs">GPS Trajectory ({polylineCoords.length} pts)</span>
          </Tooltip>
        </Polyline>
      )}

      {/* GPS Observation Markers */}
      {showObservations &&
        validPoints.map(({ point, coord, index }) => (
          <CircleMarker
            key={`gps-${index}`}
            center={coord}
            radius={4}
            pathOptions={{
              color: '#0891b2', // cyan-600 border
              weight: 1.5,
              fillColor: '#22d3ee', // cyan-400 fill
              fillOpacity: 0.9,
            }}
          >
            <Popup className="dark-popup">
              <div className="p-1 space-y-1 text-xs font-sans">
                <div className="font-bold text-cyan-400 border-b border-slate-700 pb-1">
                  GPS Observation #{index + 1}
                </div>
                <div className="font-mono text-[11px] text-slate-300">
                  <div>Lat: {coord[0].toFixed(6)}</div>
                  <div>Lon: {coord[1].toFixed(6)}</div>
                  {point.speed !== undefined && <div>Speed: {point.speed} m/s</div>}
                  {point.timestamp && <div>Time: {String(point.timestamp)}</div>}
                </div>
              </div>
            </Popup>
          </CircleMarker>
        ))}
    </>
  );
};
