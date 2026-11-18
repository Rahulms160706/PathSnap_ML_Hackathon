import React, { useState, useEffect, useCallback } from 'react';
import {
  Cpu,
  GitCompare,
  Sliders,
  Award,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Clock,
  BarChart3,
  HelpCircle,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { useBackendHealth } from '../hooks/useBackendHealth';
import { pathsnapService } from '../services/pathsnapService';
import { ModelComparisonResponse, ModelBenchmarkItem } from '../types/api';

export const ModelAnalyticsPage: React.FC = () => {
  const { data: healthData, isHealthy } = useBackendHealth(10000);
  const [comparisonData, setComparisonData] = useState<ModelComparisonResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const placeholderFamilies = pathsnapService.getPlaceholderModelFamilies();

  const loadComparison = useCallback(async () => {
    setIsLoading(true);
    try {
      const result = await pathsnapService.getModelComparison();
      if (result && result.models && result.models.length > 0) {
        setComparisonData(result);
        setLastUpdated(new Date().toLocaleTimeString());
      } else {
        setComparisonData(null);
      }
    } catch (e) {
      console.warn('GET /api/models/comparison not yet available on Laptop 1', e);
      setComparisonData(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadComparison();
  }, [loadComparison]);

  // Determine active model list: real backend data if returned, else placeholder families
  const isLiveData = Boolean(comparisonData && comparisonData.models && comparisonData.models.length > 0);
  const displayModels: ModelBenchmarkItem[] = isLiveData
    ? comparisonData!.models
    : placeholderFamilies;

  // Selected champion model from backend
  const selectedModelName = comparisonData?.selected_model_name || healthData?.active_model;
  const selectionCriterion = comparisonData?.selection_criterion;

  // Format Recharts data when real metrics exist
  const chartData = displayModels
    .filter((m) => !m.is_placeholder && m.macro_f1 !== undefined)
    .map((m) => ({
      name: m.model_name.length > 15 ? m.model_name.slice(0, 14) + '…' : m.model_name,
      family: m.model_family,
      'Macro F1': Number((m.macro_f1! * 100).toFixed(1)),
      Accuracy: m.accuracy !== undefined ? Number((m.accuracy * 100).toFixed(1)) : undefined,
      'Log Loss': m.log_loss !== undefined ? Number(m.log_loss.toFixed(3)) : undefined,
    }));

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-fade-in">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-emerald-400">
            <Cpu className="w-4 h-4" />
            <span>Laptop 1 ML Model Evaluation</span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight sm:text-3xl mt-1">
            Model Benchmarks & Optimization
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            Live comparative performance across the five required model families, Bayesian hyperparameter optimization, and sequence decoding criteria evaluated on Laptop 1.
          </p>
        </div>

        {/* Action Controls & Backend Status */}
        <div className="flex items-center gap-3">
          <button
            onClick={loadComparison}
            disabled={isLoading}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700 text-xs font-medium transition-all"
            title="Check GET /api/models/comparison on Laptop 1"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-emerald-400' : ''}`} />
            <span>Check Laptop 1 Updates</span>
          </button>

          {/* Selected Champion Card */}
          <div className="px-4 py-3 rounded-2xl bg-emerald-950/40 border border-emerald-500/30 flex items-center gap-3">
            <div className="p-2 rounded-xl bg-emerald-500/20 text-emerald-400">
              <Award className="w-5 h-5" />
            </div>
            <div>
              <div className="text-[10px] uppercase font-semibold text-emerald-400 tracking-wider">
                Selected Champion Model
              </div>
              <div className="text-sm font-bold text-white font-mono">
                {selectedModelName || (isHealthy ? 'Champion Model' : 'Pending Laptop 1')}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Live Data vs Placeholder Notice Banner */}
      {isLiveData ? (
        <div className="p-3.5 rounded-2xl bg-emerald-950/40 border border-emerald-500/30 text-emerald-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>
              <strong>Live Model Benchmarks Loaded:</strong> Displaying {displayModels.length} models trained and evaluated on Laptop 1.
            </span>
          </div>
          {lastUpdated && <span className="font-mono text-[11px] opacity-80">Updated: {lastUpdated}</span>}
        </div>
      ) : (
        <div className="p-4 rounded-2xl bg-amber-950/30 border border-amber-500/30 text-amber-300 text-xs space-y-1">
          <div className="flex items-center gap-2 font-semibold">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>Specification Placeholders (Awaiting Laptop 1 Model Training Results)</span>
          </div>
          <p className="text-[11px] text-amber-200/80 pl-6 leading-relaxed">
            The five cards below represent the mandatory model families required by the hackathon guidelines. Actual trained model names, evaluation metrics, and the selected champion model will be dynamically populated from <code className="text-emerald-400 font-mono">GET /api/models/comparison</code> once your teammate finishes training on Laptop 1. No metrics or winners are hardcoded.
          </p>
        </div>
      )}

      {/* Five-Model Family Grid */}
      <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
          <div className="flex items-center gap-2 text-slate-200 font-semibold text-sm">
            <GitCompare className="w-4 h-4 text-emerald-400" />
            <span>Five-Model Family Benchmark Suite</span>
          </div>
          <span className="text-xs text-slate-400">
            {isLiveData ? 'Dynamic Server Results' : 'Required Families (Placeholder State)'}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-3.5">
          {displayModels.map((m, idx) => {
            const isWinner =
              m.is_selected ||
              (selectedModelName &&
                m.model_name.toLowerCase() === selectedModelName.toLowerCase());

            return (
              <div
                key={m.model_family || idx}
                className={`p-4 rounded-xl border flex flex-col justify-between space-y-3 transition-all ${
                  isWinner
                    ? 'bg-emerald-950/40 border-emerald-500/50 shadow-glow-emerald ring-1 ring-emerald-500/40'
                    : 'bg-slate-950/70 border-slate-800'
                }`}
              >
                <div>
                  {/* Top: Family and status badge */}
                  <div className="flex items-center justify-between text-xs mb-1.5">
                    <span className="font-semibold text-slate-300 text-[11px] uppercase tracking-wider">
                      {m.model_family}
                    </span>
                    <span
                      className={`text-[9px] px-1.5 py-0.5 rounded font-medium ${
                        isWinner
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                          : m.is_placeholder
                          ? 'bg-slate-800 text-slate-400'
                          : 'bg-teal-950/60 text-teal-300 border border-teal-500/30'
                      }`}
                    >
                      {isWinner ? 'Selected Winner' : m.is_placeholder ? 'Pending Training' : 'Evaluated'}
                    </span>
                  </div>

                  {/* Model Name */}
                  <h4 className="text-sm font-bold text-white font-mono truncate" title={m.model_name}>
                    {m.model_name}
                  </h4>

                  {/* Notes / candidates */}
                  {m.selection_notes && (
                    <p className="text-[10px] text-slate-400 mt-1 leading-snug line-clamp-2">
                      {m.selection_notes}
                    </p>
                  )}
                </div>

                {/* Metrics Section */}
                <div className="pt-2 border-t border-slate-800/80 space-y-1 text-[11px] font-mono">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Macro F1:</span>
                    <span className={m.macro_f1 !== undefined ? 'text-emerald-400 font-bold' : 'text-slate-400'}>
                      {m.macro_f1 !== undefined ? `${(m.macro_f1 * 100).toFixed(1)}%` : '—'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Accuracy:</span>
                    <span className={m.accuracy !== undefined ? 'text-slate-200' : 'text-slate-400'}>
                      {m.accuracy !== undefined ? `${(m.accuracy * 100).toFixed(1)}%` : '—'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Log Loss:</span>
                    <span className={m.log_loss !== undefined ? 'text-slate-200' : 'text-slate-400'}>
                      {m.log_loss !== undefined ? m.log_loss.toFixed(3) : '—'}
                    </span>
                  </div>
                  {m.training_time_s !== undefined && (
                    <div className="flex justify-between text-[10px] text-slate-400 pt-0.5">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3 text-slate-400" /> Train Time:
                      </span>
                      <span>{m.training_time_s}s</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Dynamic Comparison Chart */}
      <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
          <div className="flex items-center gap-2 text-slate-200 font-semibold text-sm">
            <BarChart3 className="w-4 h-4 text-emerald-400" />
            <span>Comparative Performance Chart</span>
          </div>
          <span className="text-xs text-slate-400">Macro F1 & Accuracy Comparison</span>
        </div>

        {chartData.length > 0 ? (
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="name" stroke="#64748b" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 100]} stroke="#64748b" tick={{ fontSize: 11 }} unit="%" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    borderColor: '#1e293b',
                    borderRadius: '0.75rem',
                    fontSize: '12px',
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                <Bar dataKey="Macro F1" fill="#10b981" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Accuracy" fill="#06b6d4" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="h-44 rounded-xl bg-slate-950/60 border border-slate-800 flex flex-col items-center justify-center p-6 text-center space-y-2">
            <div className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-400">
              <BarChart3 className="w-6 h-6" />
            </div>
            <p className="text-xs text-slate-300 font-medium">Comparative Chart Pending Actual Model Evaluation</p>
            <p className="text-[11px] text-slate-400 max-w-md">
              Once Laptop 1 executes model training and serves <code className="text-emerald-400">GET /api/models/comparison</code>, comparative bars for Macro F1, Accuracy, and Log Loss will render automatically.
            </p>
          </div>
        )}
      </div>

      {/* Two Column details: Selection Criteria & Optimization Strategy */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Model Selection Criteria */}
        <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
            <div className="flex items-center gap-2 text-slate-200 font-semibold text-sm">
              <Award className="w-4 h-4 text-emerald-400" />
              <span>Model Selection Justification</span>
            </div>
            <span className="text-xs font-mono text-emerald-400">
              {selectionCriterion ? 'Specified by Laptop 1' : 'Pending Selection'}
            </span>
          </div>

          <div className="space-y-3 text-xs text-slate-300">
            {selectionCriterion ? (
              <div className="p-3.5 rounded-xl bg-emerald-950/30 border border-emerald-500/30 text-emerald-200 leading-relaxed">
                {selectionCriterion}
              </div>
            ) : (
              <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800 text-slate-400 leading-relaxed text-[11px] space-y-2">
                <div className="flex items-center gap-1.5 text-slate-300 font-medium">
                  <HelpCircle className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Evaluation Selection Policy:</span>
                </div>
                <p>
                  Per the hackathon guidelines, the champion model must be chosen based on empirical evidence from 5-fold cross-validation on the student partition, balancing high Macro F1 score, calibrated emission probabilities (low log loss), and fast inference latency.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Bayesian & HMM Integration Info */}
        <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
            <div className="flex items-center gap-2 text-slate-200 font-semibold text-sm">
              <Sliders className="w-4 h-4 text-teal-400" />
              <span>Hyperparameter & HMM Search Protocol</span>
            </div>
            <span className="text-xs font-mono text-cyan-400">HMM / Viterbi</span>
          </div>

          <div className="space-y-3 text-xs text-slate-300">
            <p className="text-[11px] text-slate-400">
              Bayesian optimization search spaces and parameters tuned on Laptop 1:
            </p>
            <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800 space-y-2 font-mono text-[11px]">
              <div className="flex justify-between text-slate-400">
                <span>Optimizer:</span>
                <span className="text-slate-200">Bayesian (Optuna / Gaussian Process)</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Decoded Sequence:</span>
                <span className="text-emerald-400">HMM Transition + Viterbi</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Validation Scheme:</span>
                <span className="text-slate-200">5-Fold Grouped Stratified Split</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
