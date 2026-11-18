import React from 'react';
import { Polyline, CircleMarker, Popup, Tooltip } from 'react-leaflet';
import { RouteCoordinate } from '../../types/api';
import { toLatLngTuple } from '../../utils/geoUtils';

interface RouteLayerProps {
  route?: RouteCoordinate[];
  visible: boolean;
}

export const RouteLayer: React.FC<RouteLayerProps> = ({ route, visible }) => {
  if (!visible || !route || route.length === 0) return null;

  const positions: [number, number][] = [];
  route.forEach((pt) => {
    const latLng = toLatLngTuple(pt);
    if (latLng) {
      positions.push(latLng);
    }
  });

  if (positions.length < 2) return null;

  const startCoord = positions[0];
  const endCoord = positions[positions.length - 1];

  return (
    <>
      {/* Main Reconstructed Polyline */}
      <Polyline
        positions={positions}
        pathOptions={{
          color: '#10b981', // emerald-500
          weight: 4.5,
          opacity: 0.95,
          lineJoin: 'round',
          lineCap: 'round',
        }}
      >
        <Tooltip sticky>
          <div className="font-sans text-xs">
            <span className="font-bold text-emerald-400">Predicted HMM/Viterbi Route</span>
            <div className="text-[10px] text-slate-300 font-mono">{positions.length} coordinates</div>
          </div>
        </Tooltip>
      </Polyline>

      {/* Origin Point Marker */}
      <CircleMarker
        center={startCoord}
        radius={7}
        pathOptions={{
          color: '#047857',
          weight: 2,
          fillColor: '#34d399',
          fillOpacity: 1,
        }}
      >
        <Popup>
          <div className="text-xs p-1">
            <div className="font-bold text-emerald-400">Trip Origin (Start)</div>
            <div className="font-mono text-[10px] text-slate-300">
              {startCoord[0].toFixed(5)}, {startCoord[1].toFixed(5)}
            </div>
          </div>
        </Popup>
      </CircleMarker>

      {/* Destination Point Marker */}
      <CircleMarker
        center={endCoord}
        radius={7}
        pathOptions={{
          color: '#065f46',
          weight: 2,
          fillColor: '#10b981',
          fillOpacity: 1,
        }}
      >
        <Popup>
          <div className="text-xs p-1">
            <div className="font-bold text-emerald-400">Trip Destination (End)</div>
            <div className="font-mono text-[10px] text-slate-300">
              {endCoord[0].toFixed(5)}, {endCoord[1].toFixed(5)}
            </div>
          </div>
        </Popup>
      </CircleMarker>
    </>
  );
};
