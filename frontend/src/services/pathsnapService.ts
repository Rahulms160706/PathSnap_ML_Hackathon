import { apiClient } from './apiClient';
import {
  BackendHealthResponse,
  EvaluationTripListResponse,
  ModelComparisonResponse,
  ModelBenchmarkItem,
  PredictionRequest,
  PredictionResponse,
  TripSummary,
} from '../types/api';

export interface HealthCheckResult {
  isHealthy: boolean;
  latencyMs: number;
  data?: BackendHealthResponse;
  error?: string;
  urlChecked: string;
}

export const pathsnapService = {
  /**
   * Health check to ping Laptop 1 backend
   */
  async checkHealth(customUrl?: string): Promise<HealthCheckResult> {
    const targetUrl = customUrl ? customUrl.replace(/\/+$/, '') : apiClient.defaults.baseURL || '';
    const startTime = performance.now();

    try {
      // Try /api/health first, then /health
      let response;
      try {
        response = await apiClient.get<BackendHealthResponse>(`${targetUrl}/api/health`, {
          timeout: 4000,
        });
      } catch (err: any) {
        if (err.response && err.response.status === 404) {
          response = await apiClient.get<BackendHealthResponse>(`${targetUrl}/health`, {
            timeout: 4000,
          });
        } else {
          throw err;
        }
      }

      const latencyMs = Math.round(performance.now() - startTime);
      return {
        isHealthy: response.status === 200,
        latencyMs,
        data: response.data,
        urlChecked: targetUrl,
      };
    } catch (error: any) {
      const latencyMs = Math.round(performance.now() - startTime);
      return {
        isHealthy: false,
        latencyMs,
        error: error.message || 'Connection refused or timeout',
        urlChecked: targetUrl,
      };
    }
  },

  /**
   * Fetch available evaluation trips from Laptop 1
   */
  async getEvaluationTrips(): Promise<TripSummary[]> {
    try {
      const response = await apiClient.get<EvaluationTripListResponse | string[] | TripSummary[]>('/api/trips');
      const data = response.data;

      if (Array.isArray(data)) {
        return data.map((t) => (typeof t === 'string' ? { trip_id: t } : t));
      }

      if (data && Array.isArray((data as EvaluationTripListResponse).trips)) {
        return (data as EvaluationTripListResponse).trips.map((t) =>
          typeof t === 'string' ? { trip_id: t } : t
        );
      }

      return [];
    } catch (error: any) {
      console.warn('API /api/trips failed, trying /trips fallback', error.message);
      try {
        const fallback = await apiClient.get<any>('/trips');
        if (Array.isArray(fallback.data)) {
          return fallback.data.map((t) => (typeof t === 'string' ? { trip_id: t } : t));
        }
      } catch (fbErr) {
        // rethrow original
      }
      throw error;
    }
  },

  /**
   * Send a prediction request for an evaluator trip
   */
  async runPrediction(request: PredictionRequest): Promise<PredictionResponse> {
    try {
      const response = await apiClient.post<PredictionResponse>('/api/predict', request);
      return response.data;
    } catch (error: any) {
      console.warn('POST /api/predict failed, trying fallback /predict', error.message);
      const fallback = await apiClient.post<PredictionResponse>('/predict', request);
      return fallback.data;
    }
  },

  /**
   * Fetch 5-model benchmark comparison dynamically from Laptop 1
   * Endpoint: GET /api/models/comparison (or /models/comparison)
   */
  async getModelComparison(): Promise<ModelComparisonResponse | null> {
    try {
      const response = await apiClient.get<ModelComparisonResponse>('/api/models/comparison', {
        timeout: 5000,
      });
      return response.data;
    } catch (error: any) {
      try {
        const fallback = await apiClient.get<ModelComparisonResponse>('/models/comparison', {
          timeout: 5000,
        });
        return fallback.data;
      } catch (fbErr) {
        // Return null when endpoint is not yet provided by Laptop 1
        return null;
      }
    }
  },

  /**
   * Clearly marked specification placeholders for the 5 required families
   * strictly used until Laptop 1 trains and exposes the actual models.
   */
  getPlaceholderModelFamilies(): ModelBenchmarkItem[] {
    return [
      {
        model_name: 'Pending Laptop 1',
        model_family: 'Instance-Based',
        selection_notes: 'KNN / Radius Neighbours placeholder per hackathon guide',
        is_placeholder: true,
      },
      {
        model_name: 'Pending Laptop 1',
        model_family: 'Tree-Based',
        selection_notes: 'Decision Tree / Extra Trees placeholder per hackathon guide',
        is_placeholder: true,
      },
      {
        model_name: 'Pending Laptop 1',
        model_family: 'Ensemble',
        selection_notes: 'Random Forest / Bagging Classifier placeholder per hackathon guide',
        is_placeholder: true,
      },
      {
        model_name: 'Pending Laptop 1',
        model_family: 'Boosting',
        selection_notes: 'HistGradientBoosting / XGBoost / LightGBM placeholder per hackathon guide',
        is_placeholder: true,
      },
      {
        model_name: 'Pending Laptop 1',
        model_family: 'Neural Network',
        selection_notes: 'Multi-Layer Perceptron (MLP) placeholder per hackathon guide',
        is_placeholder: true,
      },
    ];
  },

  /**
   * Visual development mock data generator (strictly for UI inspection when backend is not connected)
   */
  getDevelopmentMocks() {
    return {
      trips: [
        { trip_id: '00000000', gps_points_count: 312, duration_seconds: 624, partition: 'evaluator_test' as const },
        { trip_id: '00000007', gps_points_count: 145, duration_seconds: 290, partition: 'evaluator_test' as const },
        { trip_id: '00000009', gps_points_count: 420, duration_seconds: 840, partition: 'evaluator_test' as const },
        { trip_id: '00000040', gps_points_count: 288, duration_seconds: 576, partition: 'evaluator_test' as const },
        { trip_id: '00000052', gps_points_count: 98, duration_seconds: 196, partition: 'evaluator_test' as const },
      ],
      mockNotice: 'VISUAL DEMO MODE ONLY - NOT REAL EVALUATOR DATA'
    };
  }
};
