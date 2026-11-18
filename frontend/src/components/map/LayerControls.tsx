import React, { useState } from 'react';
import { Layers, ChevronDown, ChevronUp } from 'lucide-react';

export interface LayerVisibilityState {
  gpsObservations: boolean;
  gpsTrajectory: boolean;
  roadNetwork: boolean;
  predictedRoute: boolean;
  referenceRoute: boolean;
}

interface LayerControlsProps {
  layers: LayerVisibilityState;
  onChange: (key: keyof LayerVisibilityState, val: boolean) => void;
  gpsPointsCount?: number;
  predictedPointsCount?: number;
  referencePointsCount?: number;
  roadArcsCount?: number;
}

export const LayerControls: React.FC<LayerControlsProps> = ({
  layers,
  onChange,
  gpsPointsCount = 0,
  predictedPointsCount = 0,
  referencePointsCount = 0,
  roadArcsCount = 0,
}) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(true);

  return (
    <div className="bg-slate-900/90 backdrop-blur-md border border-slate-800 rounded-xl shadow-2xl p-3 text-xs w-60 pointer-events-auto transition-all">
      <div
        className="flex items-center justify-between cursor-pointer select-none pb-1.5 border-b border-slate-800"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-1.5 font-semibold text-slate-200 text-[11px] uppercase tracking-wider">
          <Layers className="w-3.5 h-3.5 text-emerald-400" />
          <span>Layer Controls</span>
        </div>
        <button className="text-slate-400 hover:text-slate-200">
          {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>
      </div>

      {isExpanded && (
        <div className="mt-2.5 space-y-2">
          {/* Predicted Route */}
          <label className="flex items-center justify-between cursor-pointer hover:bg-slate-800/40 p-1 rounded transition-colors">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={layers.predictedRoute}
                onChange={(e) => onChange('predictedRoute', e.target.checked)}
                className="rounded bg-slate-950 border-slate-700 text-emerald-500 focus:ring-0"
              />
              <span className="text-emerald-400 font-medium">Predicted Route</span>
            </div>
            {predictedPointsCount > 0 && (
              <span className="text-[10px] font-mono text-emerald-300 bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-500/30">
                {predictedPointsCount}
              </span>
            )}
          </label>

          {/* GPS Observations */}
          <label className="flex items-center justify-between cursor-pointer hover:bg-slate-800/40 p-1 rounded transition-colors">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={layers.gpsObservations}
                onChange={(e) => onChange('gpsObservations', e.target.checked)}
                className="rounded bg-slate-950 border-slate-700 text-cyan-500 focus:ring-0"
              />
              <span className="text-slate-200">GPS Observations</span>
            </div>
            {gpsPointsCount > 0 && (
              <span className="text-[10px] font-mono text-cyan-300 bg-cyan-950/60 px-1.5 py-0.5 rounded border border-cyan-500/30">
                {gpsPointsCount}
              </span>
            )}
          </label>

          {/* GPS Trajectory */}
          <label className="flex items-center justify-between cursor-pointer hover:bg-slate-800/40 p-1 rounded transition-colors">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={layers.gpsTrajectory}
                onChange={(e) => onChange('gpsTrajectory', e.target.checked)}
                className="rounded bg-slate-950 border-slate-700 text-cyan-500 focus:ring-0"
              />
              <span className="text-slate-300">GPS Trajectory Line</span>
            </div>
          </label>

          {/* Reference Route */}
          <label className="flex items-center justify-between cursor-pointer hover:bg-slate-800/40 p-1 rounded transition-colors">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={layers.referenceRoute}
                onChange={(e) => onChange('referenceRoute', e.target.checked)}
                disabled={referencePointsCount === 0}
                className="rounded bg-slate-950 border-slate-700 text-purple-500 focus:ring-0 disabled:opacity-40"
              />
              <span className={`${referencePointsCount > 0 ? 'text-purple-300 font-medium' : 'text-slate-500'}`}>
                Reference Route
              </span>
            </div>
            {referencePointsCount > 0 && (
              <span className="text-[10px] font-mono text-purple-300 bg-purple-950/60 px-1.5 py-0.5 rounded border border-purple-500/30">
                {referencePointsCount}
              </span>
            )}
          </label>

          {/* Road Network */}
          <label className="flex items-center justify-between cursor-pointer hover:bg-slate-800/40 p-1 rounded transition-colors">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={layers.roadNetwork}
                onChange={(e) => onChange('roadNetwork', e.target.checked)}
                disabled={roadArcsCount === 0}
                className="rounded bg-slate-950 border-slate-700 text-slate-400 focus:ring-0 disabled:opacity-40"
              />
              <span className={`${roadArcsCount > 0 ? 'text-slate-300' : 'text-slate-500'}`}>
                Road Network
              </span>
            </div>
            {roadArcsCount > 0 && (
              <span className="text-[10px] font-mono text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded border border-slate-700">
                {roadArcsCount} arcs
              </span>
            )}
          </label>
        </div>
      )}
    </div>
  );
};
