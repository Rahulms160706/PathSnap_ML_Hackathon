import React, { useState } from 'react';
import { Radio, Settings2, Laptop, Network } from 'lucide-react';
import { StatusBadge } from './StatusBadge';
import { ConnectionModal } from './ConnectionModal';
import { useBackendHealth } from '../../hooks/useBackendHealth';
import { getStoredBaseUrl } from '../../services/apiClient';

export const Header: React.FC = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const { isHealthy, latencyMs, isLoading, refresh } = useBackendHealth(10000);
  const activeUrl = getStoredBaseUrl();

  return (
    <>
      <header className="sticky top-0 z-40 w-full h-16 border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md px-6 flex items-center justify-between">
        {/* Left: Branding */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-emerald-400 to-teal-600 flex items-center justify-center shadow-glow-emerald">
              <Radio className="w-5 h-5 text-slate-950" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg font-bold tracking-tight text-white font-sans">
                  Path<span className="text-emerald-400">Snap</span>
                </span>
                <span className="px-1.5 py-0.5 text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded">
                  LAPTOP 2
                </span>
              </div>
              <p className="text-[10px] text-slate-400 font-mono tracking-tight">
                Map-Matching & Route Analytics
              </p>
            </div>
          </div>
        </div>

        {/* Right: Integration status & Settings */}
        <div className="flex items-center gap-3">
          {/* Laptop 2 Local Subnet Info */}
          <div className="hidden lg:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-400">
            <Laptop className="w-3.5 h-3.5 text-slate-400" />
            <span>Frontend Host:</span>
            <span className="font-mono text-slate-200">10.30.202.22</span>
          </div>

          {/* Target Backend IP indicator */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/90 border border-slate-800 text-xs">
            <Network className="w-3.5 h-3.5 text-emerald-400" />
            <span className="text-slate-400 hidden sm:inline">Target API:</span>
            <span className="font-mono text-emerald-300 max-w-[160px] truncate" title={activeUrl}>
              {activeUrl}
            </span>
          </div>

          {/* Connection Status Badge */}
          <StatusBadge
            status={isLoading ? 'connecting' : isHealthy ? 'connected' : 'disconnected'}
            latency={latencyMs}
          />

          {/* Settings Trigger */}
          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 hover:bg-slate-850 active:scale-95 text-slate-300 hover:text-white border border-slate-800 rounded-lg text-xs font-medium transition-all"
            title="Configure Laptop 1 backend IP address"
          >
            <Settings2 className="w-3.5 h-3.5 text-slate-400" />
            <span className="hidden md:inline">Configure IP</span>
          </button>
        </div>
      </header>

      {/* Dynamic IP Configuration Modal */}
      <ConnectionModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onConnectionUpdated={() => refresh()}
      />
    </>
  );
};
