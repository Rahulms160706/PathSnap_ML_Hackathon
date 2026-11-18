import L from 'leaflet';
import { GpsPoint, RouteCoordinate } from '../types/api';

/**
 * Normalizes any coordinate representation into standard Leaflet [lat, lon] tuple.
 * Detects whether an array [a, b] is [lat, lon] or [lon, lat] (GeoJSON standard).
 */
export function toLatLngTuple(
  pt: [number, number] | { lat?: number; latitude?: number; lon?: number; lng?: number; longitude?: number }
): [number, number] | null {
  if (!pt) return null;

  if (Array.isArray(pt)) {
    if (pt.length < 2) return null;
    let [a, b] = pt;
    if (typeof a !== 'number' || typeof b !== 'number') return null;

    // Detection heuristic: Latitude is between -90 and 90, Longitude is -180 to 180.
    // If a > 90 or a < -90, then a is longitude, b is latitude.
    // In India (Bangalore data): Lat is ~12.x to 13.x, Lon is ~77.x to 78.x.
    if (a > 60 && a < 90 && b > 0 && b < 40) {
      // a is ~77, b is ~12 -> GeoJSON [lon, lat] -> invert to [lat, lon]
      return [b, a];
    }
    if (Math.abs(a) <= 90 && Math.abs(b) <= 180) {
      return [a, b];
    }
    return [b, a];
  }

  const lat = pt.lat ?? pt.latitude;
  const lon = pt.lon ?? pt.lng ?? pt.longitude;

  if (typeof lat === 'number' && typeof lon === 'number') {
    return [lat, lon];
  }

  return null;
}

/**
 * Converts a list of GPS points or Route coordinates to an array of [lat, lon] for Leaflet
 */
export function extractLatLngList(points?: (GpsPoint | RouteCoordinate | [number, number])[]): [number, number][] {
  if (!points || !Array.isArray(points)) return [];

  const results: [number, number][] = [];
  for (const p of points) {
    const latLng = toLatLngTuple(p as any);
    if (latLng) {
      results.push(latLng);
    }
  }
  return results;
}

/**
 * Calculates the bounding box for a list of coordinates
 */
export function getBoundsForCoordinates(coords: [number, number][]): L.LatLngBounds | null {
  if (!coords || coords.length === 0) return null;

  try {
    const bounds = L.latLngBounds(coords[0], coords[0]);
    for (let i = 1; i < coords.length; i++) {
      bounds.extend(coords[i]);
    }
    return bounds;
  } catch (e) {
    console.error('Failed to compute bounds', e);
    return null;
  }
}
