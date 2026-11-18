import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  MapPin,
  Cpu,
  Layers,
  FileText,
  Activity,
  GitBranch,
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const navItems = [
    {
      to: '/',
      label: 'System Overview',
      icon: LayoutDashboard,
      badge: 'Live',
    },
    {
      to: '/evaluation',
      label: 'Route Evaluation',
      icon: MapPin,
      badge: 'Evaluator',
    },
    {
      to: '/models',
      label: 'Model Analytics',
      icon: Cpu,
    },
  ];

  return (
    <aside className="w-64 border-r border-slate-800/80 bg-slate-950 flex flex-col justify-between shrink-0 select-none">
      <div className="p-4 space-y-6">
        {/* Navigation list */}
        <div>
          <div className="px-3 mb-2 text-[11px] font-semibold tracking-wider text-slate-400 uppercase font-mono">
            Navigation
          </div>
          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-medium transition-all ${
                      isActive
                        ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/25 shadow-glow-emerald'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900 border border-transparent'
                    }`
                  }
                >
                  <div className="flex items-center gap-3">
                    <Icon className="w-4 h-4 shrink-0" />
                    <span>{item.label}</span>
                  </div>
                  {item.badge && (
                    <span className="px-1.5 py-0.5 text-[9px] font-semibold bg-slate-800 text-slate-300 rounded border border-slate-700">
                      {item.badge}
                    </span>
                  )}
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* System Architecture Box */}
        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800/80 space-y-2 text-xs">
          <div className="flex items-center gap-1.5 text-slate-300 font-semibold">
            <Layers className="w-3.5 h-3.5 text-emerald-400" />
            <span>Architecture</span>
          </div>
          <div className="space-y-1.5 text-[11px] text-slate-400">
            <div className="flex justify-between items-center py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Laptop 1:</span>
              <span className="text-emerald-400 font-mono">ML & FastAPI</span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Laptop 2:</span>
              <span className="text-teal-400 font-mono">React UI</span>
            </div>
            <div className="flex justify-between items-center pt-0.5">
              <span className="text-slate-400">Pipeline:</span>
              <span className="text-slate-300 font-mono text-[10px]">HMM / Viterbi</span>
            </div>
          </div>
        </div>

        {/* Hackathon Specs pill */}
        <div className="px-3.5 py-2.5 rounded-xl bg-slate-900/40 border border-slate-800/50 space-y-1 text-[11px]">
          <div className="flex items-center gap-1.5 text-slate-400 font-medium">
            <Activity className="w-3.5 h-3.5 text-emerald-400" />
            <span>Dataset Partitions</span>
          </div>
          <div className="flex items-center justify-between text-slate-400 text-[10px]">
            <span>Evaluator Trips:</span>
            <span className="text-emerald-300 font-mono">10 trips</span>
          </div>
          <div className="flex items-center justify-between text-slate-400 text-[10px]">
            <span>Student Test:</span>
            <span className="text-slate-300 font-mono">10 trips</span>
          </div>
        </div>
      </div>

      {/* Footer Info */}
      <div className="p-4 border-t border-slate-800/80 text-[11px] text-slate-400 space-y-1.5">
        <div className="flex items-center justify-between font-mono">
          <span className="flex items-center gap-1">
            <GitBranch className="w-3 h-3 text-slate-400" />
            v1.0-eval
          </span>
          <span className="text-emerald-500 font-semibold">PES RR ML</span>
        </div>
        <div className="text-[10px] text-slate-400 flex items-center gap-1">
          <FileText className="w-3 h-3 text-slate-400" />
          <span>Zero-Leakage Evaluator Mode</span>
        </div>
      </div>
    </aside>
  );
};
