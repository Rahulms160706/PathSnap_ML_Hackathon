export interface BackendHealthResponse {
  status: 'healthy' | 'degraded' | 'error';
  version?: string;
  active_model?: string;
  device?: string;
  evaluator_trips_count?: number;
  message?: string;
  timestamp?: string;
}

export interface TripSummary {
  trip_id: string;
  gps_points_count?: number;
  duration_seconds?: number;
  start_time?: string;
  partition?: 'evaluator_test' | 'student_test' | 'train';
}

export interface EvaluationTripListResponse {
  trips: (string | TripSummary)[];
  count?: number;
}

export interface GpsPoint {
  lat: number;
  lon: number;
  timestamp?: number | string;
  speed?: number;
  accuracy?: number;
}

export interface RouteCoordinate {
  lat: number;
  lon: number;
  arc_id?: number | string;
  segment_index?: number;
}

export interface EvaluationMetrics {
  accuracy?: number;
  precision?: number;
  recall?: number;
  macro_f1?: number;
  log_loss?: number;
  route_continuity?: number;
  inference_time_ms?: number;
  classifier_time_ms?: number;
  viterbi_time_ms?: number;
  total_arcs_matched?: number;
  arcs_correct?: number;
  [key: string]: number | undefined;
}

export interface ModelMetadata {
  classifier?: string;
  decoder?: string;
  hyperparameters?: Record<string, any>;
  transition_beta?: number;
  emission_sigma?: number;
  candidate_radius_m?: number;
  features_used?: string[];
}

export interface RoadArcGeometry {
  arc_id: number | string;
  from_node: number | string;
  to_node: number | string;
  coordinates: [number, number][]; // [[lat, lon], ...]
}

export interface PredictionResponse {
  trip_id: string;
  success: boolean;
  gps_trajectory: GpsPoint[];
  predicted_route: RouteCoordinate[];
  reference_route?: RouteCoordinate[]; // Only present if permitted and returned by evaluator backend
  road_network?: RoadArcGeometry[];
  metrics?: EvaluationMetrics;
  model_info?: ModelMetadata;
  inference_time_ms?: number;
  message?: string;
}

export interface PredictionRequest {
  trip_id: string;
  include_metrics?: boolean;
  include_road_network?: boolean;
  model_override?: string;
}

export interface ConnectionConfig {
  baseUrl: string;
  isCustom: boolean;
  timeoutMs: number;
}

export interface ModelBenchmarkItem {
  model_name: string;
  model_family: string;
  accuracy?: number;
  precision?: number;
  recall?: number;
  macro_f1?: number;
  log_loss?: number;
  training_time_s?: number;
  inference_time_ms?: number;
  hyperparameters?: Record<string, any>;
  is_selected?: boolean;
  selection_notes?: string;
  is_placeholder?: boolean;
}

export interface ModelComparisonResponse {
  models: ModelBenchmarkItem[];
  selected_model_name?: string;
  selection_criterion?: string;
  comparison_dataset?: string;
  timestamp?: string;
}

