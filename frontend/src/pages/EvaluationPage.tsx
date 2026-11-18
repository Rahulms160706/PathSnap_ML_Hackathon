import React, { useState, useEffect, useCallback } from 'react';
import {
  MapPin,
  Play,
  RotateCcw,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  Eye,
  SlidersHorizontal,
} from 'lucide-react';
import { useBackendHealth } from '../hooks/useBackendHealth';
import { pathsnapService } from '../services/pathsnapService';
import { PredictionResponse, TripSummary } from '../types/api';
import { MapContainer } from '../components/map/MapContainer';
import { LayerVisibilityState } from '../components/map/LayerControls';
import { MetricsGrid } from '../components/metrics/MetricsGrid';
import { DEV_AVAILABLE_TRIPS, DEV_SAMPLE_PREDICTION } from '../fixtures/devFixtures';

export const EvaluationPage: React.FC = () => {
  const { isHealthy } = useBackendHealth(10000);

  // Evaluation Trips state
  const [trips, setTrips] = useState<TripSummary[]>(DEV_AVAILABLE_TRIPS);
  const [selectedTrip, setSelectedTrip] = useState<string>('00000000');
  const [, setIsLoadingTrips] = useState<boolean>(false);

  // Prediction and Map Data state
  const [predictionData, setPredictionData] = useState<PredictionResponse | null>(null);
  const [isRunningPrediction, setIsRunningPrediction] = useState<boolean>(false);
  const [predictionError, setPredictionError] = useState<string | null>(null);
  const [isDevFixture, setIsDevFixture] = useState<boolean>(false);

  // Layer Visibility State
  const [layers, setLayers] = useState<LayerVisibilityState>({
    gpsObservations: true,
    gpsTrajectory: true,
    roadNetwork: true,
    predictedRoute: true,
    referenceRoute: true,
  });

  // Fetch available evaluator trips from Laptop 1
  const loadTrips = useCallback(async () => {
    setIsLoadingTrips(true);
    try {
      const fetched = await pathsnapService.getEvaluationTrips();
      if (fetched && fetched.length > 0) {
        setTrips(fetched);
        if (!fetched.some((t) => t.trip_id === selectedTrip)) {
          setSelectedTrip(fetched[0].trip_id);
        }
      }
    } catch (err: any) {
      console.warn('Backend trips unavailable, using standard evaluator trip IDs', err.message);
      setTrips(DEV_AVAILABLE_TRIPS);
    } finally {
      setIsLoadingTrips(false);
    }
  }, [selectedTrip]);

  useEffect(() => {
    loadTrips();
  }, [loadTrips]);

  // Execute Route Reconstruction via Laptop 1 API
  const handleRunReconstruction = async () => {
    setIsRunningPrediction(true);
    setPredictionError(null);

    try {
      const response = await pathsnapService.runPrediction({
        trip_id: selectedTrip,
        include_metrics: true,
        include_road_network: true,
      });

      if (response && response.success) {
        setPredictionData(response);
        setIsDevFixture(false);
      } else {
        throw new Error(response?.message || 'Prediction failed without error details from backend');
      }
    } catch (error: any) {
      const errorMsg =
        error.response?.data?.detail ||
        error.message ||
        'Failed to connect to Laptop 1 backend. Ensure FastAPI is running with --host 0.0.0.0';
      setPredictionError(errorMsg);
    } finally {
      setIsRunningPrediction(false);
    }
  };

  // Offline development preview loader
  const handleLoadDevPreview = () => {
    setPredictionData(DEV_SAMPLE_PREDICTION);
    setIsDevFixture(true);
    setPredictionError(null);
  };

  const handleLayerChange = (key: keyof LayerVisibilityState, val: boolean) => {
    setLayers((prev) => ({ ...prev, [key]: val }));
  };

  const handleResetView = () => {
    setPredictionData(null);
    setPredictionError(null);
    setIsDevFixture(false);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] bg-slate-950 overflow-hidden">
      {/* Top Evaluator Control Bar */}
      <div className="h-16 border-b border-slate-800 bg-slate-900/70 backdrop-blur-md px-6 flex items-center justify-between shrink-0 z-10">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <MapPin className="w-4 h-4" />
            </div>
            <span className="text-xs font-semibold text-slate-200 uppercase tracking-wider">
              Evaluator Trip:
            </span>
          </div>

          {/* Trip Selector Dropdown */}
          <div className="relative">
            <select
              value={selectedTrip}
              onChange={(e) => {
                setSelectedTrip(e.target.value);
                setPredictionError(null);
              }}
              disabled={isRunningPrediction}
              className="px-3.5 py-1.5 bg-slate-950 border border-slate-700 hover:border-slate-600 rounded-xl text-xs font-mono text-emerald-300 focus:outline-none focus:border-emerald-500 transition-colors"
            >
              {trips.map((t) => (
                <option key={t.trip_id} value={t.trip_id}>
                  Trip {t.trip_id} {t.gps_points_count ? `(${t.gps_points_count} pts)` : ''}
                </option>
              ))}
            </select>
          </div>

          {/* Run Reconstruction Button */}
          <button
            onClick={handleRunReconstruction}
            disabled={isRunningPrediction}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-400 hover:bg-emerald-300 disabled:opacity-50 text-slate-950 font-bold text-xs shadow-glow-emerald transition-all active:scale-95"
          >
            {isRunningPrediction ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Running Viterbi...</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Run Reconstruction</span>
              </>
            )}
          </button>

          {/* Clear / Reset button */}
          {predictionData && (
            <button
              onClick={handleResetView}
              className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-xl transition-colors"
              title="Reset map view"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Right side status & action buttons */}
        <div className="flex items-center gap-3">
          {/* Offline / Preview button */}
          {!isHealthy && !predictionData && (
            <button
              onClick={handleLoadDevPreview}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-300 hover:text-white border border-slate-700 text-xs transition-colors"
            >
              <Eye className="w-3.5 h-3.5 text-teal-400" />
              <span>Load Offline Test Fixture</span>
            </button>
          )}

          {isDevFixture && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-amber-950/60 border border-amber-500/40 text-amber-300 text-[11px] font-mono">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
              <span>Dev Fixture Mode</span>
            </div>
          )}

          {predictionData && !isDevFixture && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 text-[11px] font-mono">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span>Live Reconstructed</span>
            </div>
          )}
        </div>
      </div>

      {/* Error Banner when prediction fails */}
      {predictionError && (
        <div className="bg-rose-950/70 border-b border-rose-500/40 px-6 py-2.5 flex items-center justify-between text-xs text-rose-300 shrink-0">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>
              <strong>Prediction Error:</strong> {predictionError}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleLoadDevPreview}
              className="underline hover:text-rose-100 font-semibold text-[11px]"
            >
              View offline map test fixture instead
            </button>
          </div>
        </div>
      )}

      {/* Workspace Area: Map (Left) + Metrics Panel (Right) */}
      <div className="flex-1 flex overflow-hidden">
        {/* Interactive Map Viewport */}
        <div className="flex-1 relative bg-slate-950">
          {predictionData ? (
            <MapContainer
              gpsTrajectory={predictionData.gps_trajectory}
              predictedRoute={predictionData.predicted_route}
              referenceRoute={predictionData.reference_route}
              roadNetwork={predictionData.road_network}
              layers={layers}
              onLayerChange={handleLayerChange}
              isLoading={isRunningPrediction}
            />
          ) : (
            /* Empty State before prediction is run */
            <div className="w-full h-full flex flex-col items-center justify-center p-8 bg-slate-950/80">
              <div className="max-w-md w-full p-8 rounded-3xl bg-slate-900/60 border border-slate-800 shadow-2xl backdrop-blur-md text-center space-y-4">
                <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto shadow-glow-emerald">
                  <SlidersHorizontal className="w-8 h-8" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white font-sans">
                    Map-Matching Engine Ready
                  </h3>
                  <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
                    Select an evaluator trip ID from the top bar and click{' '}
                    <strong className="text-emerald-400">Run Reconstruction</strong> to trigger
                    HMM candidate scoring and Viterbi sequence decoding on Laptop 1.
                  </p>
                </div>
                <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
                  <button
                    onClick={handleRunReconstruction}
                    disabled={isRunningPrediction}
                    className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-emerald-400 hover:bg-emerald-300 text-slate-950 font-bold text-xs shadow-glow-emerald transition-all active:scale-95"
                  >
                    Run Trip {selectedTrip}
                  </button>
                  <button
                    onClick={handleLoadDevPreview}
                    className="w-full sm:w-auto px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-750 text-slate-300 hover:text-white border border-slate-700 text-xs transition-colors"
                  >
                    Load Offline Preview
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Evaluation Metrics Sidebar */}
        <div className="w-84 border-l border-slate-800 bg-slate-950/95 p-5 overflow-y-auto shrink-0 shadow-2xl">
          <MetricsGrid
            metrics={predictionData?.metrics}
            modelInfo={predictionData?.model_info}
            inferenceTimeMs={predictionData?.inference_time_ms}
            isDevFixture={isDevFixture}
          />
        </div>
      </div>
    </div>
  );
};
