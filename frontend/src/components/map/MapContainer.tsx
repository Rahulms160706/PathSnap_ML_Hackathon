import React, { useMemo } from 'react';
import { MapContainer as LeafletMap, TileLayer, ZoomControl } from 'react-leaflet';
import { GpsPoint, RouteCoordinate, RoadArcGeometry } from '../../types/api';
import { extractLatLngList } from '../../utils/geoUtils';
import { FitBounds } from './FitBounds';
import { GpsLayer } from './GpsLayer';
import { RouteLayer } from './RouteLayer';
import { GroundTruthLayer } from './GroundTruthLayer';
import { RoadNetworkLayer } from './RoadNetworkLayer';
import { MapLegend } from './MapLegend';
import { LayerControls, LayerVisibilityState } from './LayerControls';

interface MapContainerProps {
  gpsTrajectory?: GpsPoint[];
  predictedRoute?: RouteCoordinate[];
  referenceRoute?: RouteCoordinate[];
  roadNetwork?: RoadArcGeometry[];
  layers: LayerVisibilityState;
  onLayerChange: (key: keyof LayerVisibilityState, val: boolean) => void;
  isLoading?: boolean;
}

export const MapContainer: React.FC<MapContainerProps> = ({
  gpsTrajectory,
  predictedRoute,
  referenceRoute,
  roadNetwork,
  layers,
  onLayerChange,
  isLoading = false,
}) => {
  // Collect all coordinates to compute bounding box for auto-fit
  const allCoordinates = useMemo(() => {
    const coords: [number, number][] = [];
    coords.push(...extractLatLngList(predictedRoute));
    coords.push(...extractLatLngList(gpsTrajectory));
    coords.push(...extractLatLngList(referenceRoute));

    if (roadNetwork && roadNetwork.length > 0) {
      roadNetwork.forEach((arc) => {
        coords.push(...extractLatLngList(arc.coordinates));
      });
    }

    return coords;
  }, [gpsTrajectory, predictedRoute, referenceRoute, roadNetwork]);

  // Default center if no coordinates available (PES RR / Bangalore default)
  const defaultCenter: [number, number] = useMemo(() => {
    if (allCoordinates.length > 0) {
      return allCoordinates[0];
    }
    return [12.934, 77.534];
  }, [allCoordinates]);

  return (
    <div className="relative w-full h-full bg-slate-950 overflow-hidden select-none">
      <LeafletMap
        center={defaultCenter}
        zoom={14}
        zoomControl={false}
        scrollWheelZoom={true}
        className="w-full h-full z-0"
        style={{ background: '#080d1a' }}
      >
        {/* Dark Matter Basemap Tiles */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          subdomains="abcd"
          maxZoom={20}
        />

        {/* Custom Zoom Control Positioned Top Left */}
        <ZoomControl position="topleft" />

        {/* Dynamic Auto-Fit to Route Extents */}
        <FitBounds coordinates={allCoordinates} />

        {/* 1. Road Network Layer (Background) */}
        <RoadNetworkLayer roadNetwork={roadNetwork} visible={layers.roadNetwork} />

        {/* 2. Reference Ground Truth Route (Middle Layer, if permitted) */}
        <GroundTruthLayer referenceRoute={referenceRoute} visible={layers.referenceRoute} />

        {/* 3. Predicted HMM/Viterbi Route (Prominent Emerald Layer) */}
        <RouteLayer route={predictedRoute} visible={layers.predictedRoute} />

        {/* 4. GPS Trajectory & Observation Markers (Top Layer) */}
        <GpsLayer
          points={gpsTrajectory}
          showObservations={layers.gpsObservations}
          showTrajectory={layers.gpsTrajectory}
        />
      </LeafletMap>

      {/* Top Right Floating Controls */}
      <div className="absolute top-4 right-4 z-[1000] flex flex-col items-end gap-3 pointer-events-none">
        <LayerControls
          layers={layers}
          onChange={onLayerChange}
          gpsPointsCount={gpsTrajectory?.length || 0}
          predictedPointsCount={predictedRoute?.length || 0}
          referencePointsCount={referenceRoute?.length || 0}
          roadArcsCount={roadNetwork?.length || 0}
        />
      </div>

      {/* Bottom Left Floating Legend */}
      <div className="absolute bottom-6 left-4 z-[1000] pointer-events-none">
        <MapLegend
          hasReferenceRoute={Boolean(referenceRoute && referenceRoute.length > 0)}
          hasRoadNetwork={Boolean(roadNetwork && roadNetwork.length > 0)}
        />
      </div>

      {/* Loading Overlay */}
      {isLoading && (
        <div className="absolute inset-0 z-[1001] bg-slate-950/70 backdrop-blur-xs flex items-center justify-center">
          <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl flex items-center gap-3 text-emerald-400">
            <div className="w-5 h-5 border-2 border-emerald-400 border-t-transparent rounded-full animate-spin" />
            <span className="text-xs font-semibold tracking-wide">Executing Viterbi Map-Matching...</span>
          </div>
        </div>
      )}
    </div>
  );
};
