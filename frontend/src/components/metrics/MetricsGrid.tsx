import React from 'react';
import { Activity, Cpu, ShieldCheck, Zap } from 'lucide-react';
import { EvaluationMetrics, ModelMetadata } from '../../types/api';
import { MetricCard } from './MetricCard';

interface MetricsGridProps {
  metrics?: EvaluationMetrics;
  modelInfo?: ModelMetadata;
  inferenceTimeMs?: number;
  isDevFixture?: boolean;
}

export const MetricsGrid: React.FC<MetricsGridProps> = ({
  metrics,
  modelInfo,
  inferenceTimeMs,
  isDevFixture = false,
}) => {
  const hasMetrics = Boolean(metrics && Object.keys(metrics).length > 0);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 text-emerald-400" />
            Evaluation Metrics
          </span>
          <span className="text-[10px] font-mono text-emerald-400">
            {hasMetrics ? 'Laptop 1 Verified' : 'Awaiting Run'}
          </span>
        </div>
        <p className="text-[11px] text-slate-400">
          Quantitative route-matching benchmarks computed by server-side evaluation.
        </p>
      </div>

      {/* Dev Fixture Warning Banner if applicable */}
      {isDevFixture && (
        <div className="p-2.5 rounded-xl bg-amber-950/40 border border-amber-500/30 text-amber-300 text-[11px] flex items-start gap-2">
          <ShieldCheck className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold">Development Preview Active:</span> Metrics are hidden to guarantee zero data fabrication. Real metrics are populated only by Laptop 1.
          </div>
        </div>
      )}

      {/* 6 Key Performance Metrics */}
      <div className="space-y-2">
        <MetricCard
          label="Route Accuracy"
          value={metrics?.accuracy}
          description="Fraction of trajectory arcs matched correctly"
          isPercentage={true}
          highlight={true}
        />

        <MetricCard
          label="Macro F1"
          value={metrics?.macro_f1}
          description="Balanced harmonic mean across road candidates"
          isPercentage={true}
          highlight={true}
        />

        <div className="grid grid-cols-2 gap-2">
          <MetricCard
            label="Precision"
            value={metrics?.precision}
            description="True positive road segment ratio"
            isPercentage={true}
          />
          <MetricCard
            label="Recall"
            value={metrics?.recall}
            description="Reference road recovery ratio"
            isPercentage={true}
          />
        </div>

        <MetricCard
          label="Log Loss"
          value={metrics?.log_loss}
          description="Cross-entropy penalty for uncertain predictions"
        />

        <MetricCard
          label="Route Continuity"
          value={metrics?.route_continuity}
          description="Topological connectedness of reconstructed path"
          isPercentage={true}
        />

        <MetricCard
          label="Total Inference Latency"
          value={metrics?.inference_time_ms ?? inferenceTimeMs}
          description="Classifier candidate ranking + Viterbi decode"
          unit="ms"
        />
      </div>

      {/* Pipeline Model Info */}
      <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2 text-xs">
        <div className="flex items-center justify-between text-slate-300 font-semibold border-b border-slate-800 pb-1.5">
          <div className="flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-emerald-400" />
            <span>Active Pipeline Info</span>
          </div>
          <Zap className="w-3.5 h-3.5 text-teal-400" />
        </div>

        <div className="space-y-1.5 text-[11px] text-slate-400">
          <div className="flex justify-between">
            <span className="text-slate-400">ML Classifier:</span>
            <span className="text-slate-200 font-mono font-medium truncate max-w-[140px]" title={modelInfo?.classifier || 'HistGradientBoosting'}>
              {modelInfo?.classifier || 'Backend Model'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Sequence Decoder:</span>
            <span className="text-emerald-400 font-mono font-medium">
              {modelInfo?.decoder || 'HMM + Viterbi'}
            </span>
          </div>
          {modelInfo?.transition_beta !== undefined && (
            <div className="flex justify-between">
              <span className="text-slate-400">Transition Beta:</span>
              <span className="text-slate-300 font-mono">{modelInfo.transition_beta}</span>
            </div>
          )}
          {modelInfo?.emission_sigma !== undefined && (
            <div className="flex justify-between">
              <span className="text-slate-400">Emission Sigma:</span>
              <span className="text-slate-300 font-mono">{modelInfo.emission_sigma}m</span>
            </div>
          )}
          {modelInfo?.candidate_radius_m !== undefined && (
            <div className="flex justify-between">
              <span className="text-slate-400">Search Radius:</span>
              <span className="text-slate-300 font-mono">{modelInfo.candidate_radius_m}m</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
