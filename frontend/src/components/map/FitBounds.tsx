import React, { useEffect } from 'react';
import { useMap } from 'react-leaflet';
import { getBoundsForCoordinates } from '../../utils/geoUtils';

interface FitBoundsProps {
  coordinates: [number, number][];
}

export const FitBounds: React.FC<FitBoundsProps> = ({ coordinates }) => {
  const map = useMap();

  useEffect(() => {
    if (!coordinates || coordinates.length === 0) return;

    const bounds = getBoundsForCoordinates(coordinates);
    if (bounds && bounds.isValid()) {
      map.fitBounds(bounds, {
        padding: [60, 60],
        maxZoom: 16,
        animate: true,
      });
    }
  }, [coordinates, map]);

  return null;
};
