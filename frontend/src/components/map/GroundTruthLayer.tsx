import React from 'react';
import { Polyline, Tooltip } from 'react-leaflet';
import { RouteCoordinate } from '../../types/api';
import { toLatLngTuple } from '../../utils/geoUtils';

interface GroundTruthLayerProps {
  referenceRoute?: RouteCoordinate[];
  visible: boolean;
}

export const GroundTruthLayer: React.FC<GroundTruthLayerProps> = ({
  referenceRoute,
  visible,
}) => {
  // STRICT RULE: Only render if explicitly supplied by backend evaluation response
  if (!visible || !referenceRoute || referenceRoute.length === 0) return null;

  const positions: [number, number][] = [];
  referenceRoute.forEach((pt) => {
    const latLng = toLatLngTuple(pt);
    if (latLng) {
      positions.push(latLng);
    }
  });

  if (positions.length < 2) return null;

  return (
    <Polyline
      positions={positions}
      pathOptions={{
        color: '#a855f7', // purple-500
        weight: 3.5,
        opacity: 0.85,
        dashArray: '8, 8',
      }}
    >
      <Tooltip sticky>
        <div className="font-sans text-xs">
          <span className="font-bold text-purple-400">Reference Ground Truth Route</span>
          <div className="text-[10px] text-slate-300 font-mono">
            {positions.length} coordinates (Authorized Backend Evaluation Layer)
          </div>
        </div>
      </Tooltip>
    </Polyline>
  );
};
