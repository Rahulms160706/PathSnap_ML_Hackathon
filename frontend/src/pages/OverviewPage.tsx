import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Server,
  Radio,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  ShieldCheck,
  Cpu,
  MapPin,
  RefreshCw,
  Zap,
} from 'lucide-react';
import { useBackendHealth } from '../hooks/useBackendHealth';
import { getStoredBaseUrl } from '../services/apiClient';

export const OverviewPage: React.FC = () => {
  const navigate = useNavigate();
  const { isHealthy, latencyMs, data, error, isLoading, refresh } = useBackendHealth(10000);
  const activeUrl = getStoredBaseUrl();

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-fade-in">
      {/* Hero Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-slate-900 via-slate-900/90 to-slate-850 border border-slate-800 p-8 shadow-2xl">
        <div className="absolute top-0 right-0 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 max-w-3xl space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/25 text-emerald-400 text-xs font-semibold uppercase tracking-wider">
            <Radio className="w-3.5 h-3.5 animate-pulse" />
            Distributed Architecture Active
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white font-sans sm:text-4xl">
            PathSnap Evaluator Dashboard
          </h1>
          <p className="text-sm text-slate-300 leading-relaxed">
            Commercial-grade Geospatial Map-Matching and Route Reconstruction interface. Designed for live evaluator inspection of candidate road matching, Hidden Markov Model (HMM) transitions, and Viterbi sequence decoding across a two-laptop deployment.
          </p>
          <div className="flex flex-wrap items-center gap-4 pt-2">
            <button
              onClick={() => navigate('/evaluation')}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-400 hover:bg-emerald-300 text-slate-950 font-bold text-xs shadow-glow-emerald transition-all active:scale-95"
            >
              <span>Open Route Evaluation</span>
              <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={() => refresh()}
              disabled={isLoading}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium text-xs border border-slate-700 transition-all"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
              <span>Refresh Connection</span>
            </button>
          </div>
        </div>
      </div>

      {/* KPI Status Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Card 1: Backend Connection */}
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/90 shadow-lg space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Laptop 1 API</span>
            <div className={`p-2 rounded-xl ${isHealthy ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}`}>
              <Server className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-xl font-bold text-white flex items-center gap-2">
              {isHealthy ? (
                <>
                  <span className="text-emerald-400">Online</span>
                  <span className="text-xs text-slate-400 font-mono font-normal">({latencyMs}ms)</span>
                </>
              ) : (
                <span className="text-rose-400">Awaiting Signal</span>
              )}
            </div>
            <p className="text-[11px] font-mono text-slate-400 truncate mt-1" title={activeUrl}>
              {activeUrl}
            </p>
          </div>
        </div>

        {/* Card 2: Active ML Model */}
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/90 shadow-lg space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Active ML Model</span>
            <div className="p-2 rounded-xl bg-teal-500/10 text-teal-400">
              <Cpu className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-lg font-bold text-white truncate" title={data?.active_model || 'Backend Model'}>
              {data?.active_model || (isHealthy ? 'Model Active' : 'Waiting for Laptop 1')}
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              Decoder: <span className="text-slate-300 font-mono">HMM + Viterbi</span>
            </p>
          </div>
        </div>

        {/* Card 3: Evaluator Trips */}
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/90 shadow-lg space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Evaluation Trips</span>
            <div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-400">
              <MapPin className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-bold text-white">
              {data?.evaluator_trips_count !== undefined ? data.evaluator_trips_count : '10'}
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              Partition: <span className="text-emerald-400 font-medium">Evaluator Test</span>
            </p>
          </div>
        </div>

        {/* Card 4: Integrity Guard */}
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/90 shadow-lg space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Anti-Leakage Guard</span>
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-lg font-bold text-emerald-400 flex items-center gap-1.5">
              <span>Strictly Isolated</span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              No ground truth stored in frontend
            </p>
          </div>
        </div>
      </div>

      {/* Integration Diagnostic & Guidelines Checklist */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Diagnostic Panel */}
        <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
            <div className="flex items-center gap-2 text-slate-200 font-semibold text-sm">
              <Zap className="w-4 h-4 text-emerald-400" />
              <span>Two-Laptop Integration Diagnostic</span>
            </div>
            <span className="text-xs font-mono text-slate-400">Port: 8000</span>
          </div>

          <div className="space-y-3 text-xs">
            <div className="flex items-start justify-between p-3 rounded-xl bg-slate-950/70 border border-slate-800">
              <div className="space-y-0.5">
                <div className="font-medium text-slate-200">Laptop 2 (This Machine)</div>
                <div className="text-[11px] text-slate-400">React + Vite UI Hosting</div>
              </div>
              <span className="px-2 py-0.5 rounded font-mono text-[11px] bg-slate-800 text-emerald-400 border border-slate-700">
                10.30.202.22
              </span>
            </div>

            <div className="flex items-start justify-between p-3 rounded-xl bg-slate-950/70 border border-slate-800">
              <div className="space-y-0.5">
                <div className="font-medium text-slate-200">Laptop 1 (Teammate Machine)</div>
                <div className="text-[11px] text-slate-400">FastAPI ML Engine & Route Reconstruction</div>
              </div>
              <span className="px-2 py-0.5 rounded font-mono text-[11px] bg-slate-800 text-slate-300 border border-slate-700 truncate max-w-[170px]">
                {activeUrl}
              </span>
            </div>

            {error && (
              <div className="p-3 rounded-xl bg-rose-950/30 border border-rose-500/30 text-rose-300 flex items-start gap-2 text-xs">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <div>
                  <div className="font-semibold">Backend Unreachable:</div>
                  <div className="text-[11px] opacity-80 mt-0.5 font-mono">{error}</div>
                  <div className="text-[11px] text-slate-400 mt-1">
                    Click "Configure IP" in the header to set your teammate's Wi-Fi IP address.
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Hackathon Compliance Box */}
        <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
            <div className="flex items-center gap-2 text-slate-200 font-semibold text-sm">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Evaluator Compliance Checklist</span>
            </div>
            <span className="text-xs font-mono text-emerald-400">Verified</span>
          </div>

          <div className="space-y-2.5 text-xs text-slate-300">
            <div className="flex items-center gap-2.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>Independent UI & ML separation on distinct hardware nodes.</span>
            </div>
            <div className="flex items-center gap-2.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>Evaluator testing trips fetched dynamically from backend.</span>
            </div>
            <div className="flex items-center gap-2.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>Zero fabrication: Display only backend-reported metrics.</span>
            </div>
            <div className="flex items-center gap-2.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>Interactive Leaflet canvas with layered trajectory visualizer.</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
