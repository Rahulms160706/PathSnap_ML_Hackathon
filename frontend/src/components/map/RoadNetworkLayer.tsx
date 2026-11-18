import React from 'react';
import { Polyline, Tooltip } from 'react-leaflet';
import { RoadArcGeometry } from '../../types/api';
import { toLatLngTuple } from '../../utils/geoUtils';

interface RoadNetworkLayerProps {
  roadNetwork?: RoadArcGeometry[];
  visible: boolean;
}

export const RoadNetworkLayer: React.FC<RoadNetworkLayerProps> = ({
  roadNetwork,
  visible,
}) => {
  if (!visible || !roadNetwork || roadNetwork.length === 0) return null;

  return (
    <>
      {roadNetwork.map((arc, idx) => {
        const positions: [number, number][] = [];
        arc.coordinates.forEach((pt) => {
          const latLng = toLatLngTuple(pt);
          if (latLng) positions.push(latLng);
        });

        if (positions.length < 2) return null;

        return (
          <Polyline
            key={`arc-${arc.arc_id || idx}`}
            positions={positions}
            pathOptions={{
              color: '#64748b', // slate-500
              weight: 2,
              opacity: 0.5,
            }}
          >
            <Tooltip sticky>
              <div className="font-mono text-[10px] text-slate-300">
                Arc ID: {String(arc.arc_id)} (Node {String(arc.from_node)} → {String(arc.to_node)})
              </div>
            </Tooltip>
          </Polyline>
        );
      })}
    </>
  );
};
