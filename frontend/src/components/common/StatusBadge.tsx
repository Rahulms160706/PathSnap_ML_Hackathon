import React from 'react';

interface StatusBadgeProps {
  status: 'connected' | 'disconnected' | 'connecting' | 'warning';
  label?: string;
  latency?: number;
  showDot?: boolean;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  label,
  latency,
  showDot = true,
  className = '',
}) => {
  const configs = {
    connected: {
      bg: 'bg-emerald-950/70 border-emerald-500/30 text-emerald-400',
      dot: 'bg-emerald-400 shadow-glow-emerald animate-pulse',
      defaultLabel: 'Backend Connected',
    },
    disconnected: {
      bg: 'bg-rose-950/70 border-rose-500/30 text-rose-400',
      dot: 'bg-rose-500',
      defaultLabel: 'Backend Offline',
    },
    connecting: {
      bg: 'bg-amber-950/70 border-amber-500/30 text-amber-400',
      dot: 'bg-amber-400 animate-ping',
      defaultLabel: 'Checking...',
    },
    warning: {
      bg: 'bg-amber-950/70 border-amber-500/30 text-amber-400',
      dot: 'bg-amber-400',
      defaultLabel: 'Degraded',
    },
  };

  const current = configs[status] || configs.disconnected;
  const displayLabel = label || current.defaultLabel;

  return (
    <div
      className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-medium border backdrop-blur-md transition-all duration-200 ${current.bg} ${className}`}
    >
      {showDot && <span className={`w-2 h-2 rounded-full ${current.dot}`} />}
      <span>{displayLabel}</span>
      {typeof latency === 'number' && latency > 0 && (
        <span className="text-[10px] opacity-75 font-mono">({latency}ms)</span>
      )}
    </div>
  );
};
