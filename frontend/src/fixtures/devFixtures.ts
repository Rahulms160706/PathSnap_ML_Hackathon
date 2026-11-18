import { PredictionResponse, TripSummary } from '../types/api';

/**
 * OFFLINE DEVELOPMENT TEST FIXTURE
 * Strictly used for testing map canvas rendering, layer controls, and responsive UI
 * when Laptop 1 ML backend is not yet active.
 *
 * NOTE: Contains ZERO fabricated evaluation metrics (accuracy, F1, loss are omitted).
 */
export const DEV_AVAILABLE_TRIPS: TripSummary[] = [
  { trip_id: '00000000', gps_points_count: 312, duration_seconds: 624, partition: 'evaluator_test' },
  { trip_id: '00000007', gps_points_count: 145, duration_seconds: 290, partition: 'evaluator_test' },
  { trip_id: '00000009', gps_points_count: 420, duration_seconds: 840, partition: 'evaluator_test' },
  { trip_id: '00000040', gps_points_count: 288, duration_seconds: 576, partition: 'evaluator_test' },
  { trip_id: '00000052', gps_points_count: 98, duration_seconds: 196, partition: 'evaluator_test' },
];

export const DEV_SAMPLE_PREDICTION: PredictionResponse = {
  trip_id: '00000000',
  success: true,
  inference_time_ms: 38.4,
  model_info: {
    classifier: 'Offline Preview (Waiting for Laptop 1)',
    decoder: 'Viterbi Dynamic Programming',
    candidate_radius_m: 50,
  },
  gps_trajectory: [
    { lat: 12.93412, lon: 77.53421, timestamp: 1600000000, speed: 11.2 },
    { lat: 12.93485, lon: 77.53504, timestamp: 1600000005, speed: 12.4 },
    { lat: 12.93570, lon: 77.53592, timestamp: 1600000010, speed: 13.0 },
    { lat: 12.93630, lon: 77.53670, timestamp: 1600000015, speed: 10.8 },
    { lat: 12.93710, lon: 77.53765, timestamp: 1600000020, speed: 14.1 },
    { lat: 12.93795, lon: 77.53850, timestamp: 1600000025, speed: 12.0 },
    { lat: 12.93880, lon: 77.53940, timestamp: 1600000030, speed: 13.5 },
    { lat: 12.93960, lon: 77.54030, timestamp: 1600000035, speed: 11.9 },
    { lat: 12.94045, lon: 77.54125, timestamp: 1600000040, speed: 10.2 },
    { lat: 12.94130, lon: 77.54220, timestamp: 1600000045, speed: 12.8 },
  ],
  predicted_route: [
    { lat: 12.93405, lon: 77.53415, arc_id: 101, segment_index: 0 },
    { lat: 12.93480, lon: 77.53498, arc_id: 101, segment_index: 1 },
    { lat: 12.93562, lon: 77.53585, arc_id: 102, segment_index: 2 },
    { lat: 12.93625, lon: 77.53662, arc_id: 102, segment_index: 3 },
    { lat: 12.93705, lon: 77.53755, arc_id: 103, segment_index: 4 },
    { lat: 12.93790, lon: 77.53842, arc_id: 103, segment_index: 5 },
    { lat: 12.93875, lon: 77.53932, arc_id: 104, segment_index: 6 },
    { lat: 12.93955, lon: 77.54022, arc_id: 104, segment_index: 7 },
    { lat: 12.94040, lon: 77.54118, arc_id: 105, segment_index: 8 },
    { lat: 12.94125, lon: 77.54212, arc_id: 105, segment_index: 9 },
  ],
  reference_route: [
    { lat: 12.93408, lon: 77.53418, arc_id: 101 },
    { lat: 12.93482, lon: 77.53500, arc_id: 101 },
    { lat: 12.93565, lon: 77.53588, arc_id: 102 },
    { lat: 12.93628, lon: 77.53665, arc_id: 102 },
    { lat: 12.93708, lon: 77.53758, arc_id: 103 },
    { lat: 12.93792, lon: 77.53845, arc_id: 103 },
    { lat: 12.93878, lon: 77.53935, arc_id: 104 },
    { lat: 12.93958, lon: 77.54025, arc_id: 104 },
    { lat: 12.94042, lon: 77.54120, arc_id: 105 },
    { lat: 12.94128, lon: 77.54215, arc_id: 105 },
  ],
  road_network: [
    {
      arc_id: 101,
      from_node: 10,
      to_node: 11,
      coordinates: [[12.93380, 77.53390], [12.93500, 77.53520]],
    },
    {
      arc_id: 102,
      from_node: 11,
      to_node: 12,
      coordinates: [[12.93500, 77.53520], [12.93680, 77.53720]],
    },
    {
      arc_id: 103,
      from_node: 12,
      to_node: 13,
      coordinates: [[12.93680, 77.53720], [12.93850, 77.53900]],
    },
    {
      arc_id: 104,
      from_node: 13,
      to_node: 14,
      coordinates: [[12.93850, 77.53900], [12.94000, 77.54070]],
    },
    {
      arc_id: 105,
      from_node: 14,
      to_node: 15,
      coordinates: [[12.94000, 77.54070], [12.94200, 77.54300]],
    },
  ],
  // NO fabricated metrics. Metrics are undefined until computed by Laptop 1 backend.
  metrics: undefined,
};
