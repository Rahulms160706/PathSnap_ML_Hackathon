import React from 'react';

interface MapLegendProps {
  hasReferenceRoute?: boolean;
  hasRoadNetwork?: boolean;
}

export const MapLegend: React.FC<MapLegendProps> = ({
  hasReferenceRoute,
  hasRoadNetwork,
}) => {
  return (
    <div className="bg-slate-900/90 backdrop-blur-md border border-slate-800 rounded-xl p-3 shadow-xl text-xs space-y-2 pointer-events-auto">
      <div className="font-semibold text-slate-200 text-[11px] uppercase tracking-wider border-b border-slate-800 pb-1">
        Map Legend
      </div>
      <div className="space-y-1.5 text-[11px]">
        {/* GPS Observations */}
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 border border-cyan-600 shrink-0" />
          <span className="text-slate-300">Raw GPS Observations</span>
        </div>

        {/* GPS Trajectory */}
        <div className="flex items-center gap-2">
          <span className="w-4 h-0.5 border-t-2 border-dashed border-cyan-400 shrink-0" />
          <span className="text-slate-300">GPS Raw Trajectory</span>
        </div>

        {/* Predicted Route */}
        <div className="flex items-center gap-2">
          <span className="w-4 h-1 bg-emerald-400 rounded-full shadow-glow-emerald shrink-0" />
          <span className="text-emerald-300 font-medium">Predicted Route (Viterbi)</span>
        </div>

        {/* Reference Route */}
        {hasReferenceRoute && (
          <div className="flex items-center gap-2">
            <span className="w-4 h-0.5 border-t-2 border-dashed border-purple-400 shrink-0" />
            <span className="text-purple-300 font-medium">Reference Route (Backend)</span>
          </div>
        )}

        {/* Road Network */}
        {hasRoadNetwork && (
          <div className="flex items-center gap-2">
            <span className="w-4 h-0.5 bg-slate-500 shrink-0" />
            <span className="text-slate-400">Road Network Geometry</span>
          </div>
        )}
      </div>
    </div>
  );
};
