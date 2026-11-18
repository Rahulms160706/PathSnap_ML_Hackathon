import React from 'react';

interface MetricCardProps {
  label: string;
  value?: number | string;
  description: string;
  unit?: string;
  isPercentage?: boolean;
  highlight?: boolean;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  description,
  unit,
  isPercentage = false,
  highlight = false,
}) => {
  let displayValue = '—';
  if (typeof value === 'number') {
    if (isPercentage) {
      displayValue = `${(value * 100).toFixed(1)}%`;
    } else {
      displayValue = value % 1 === 0 ? String(value) : value.toFixed(3);
    }
  } else if (typeof value === 'string' && value.trim()) {
    displayValue = value;
  }

  const isEvaluated = displayValue !== '—';

  return (
    <div
      className={`p-3.5 rounded-xl border transition-all ${
        highlight && isEvaluated
          ? 'bg-emerald-950/40 border-emerald-500/40 shadow-glow-emerald'
          : 'bg-slate-900/80 border-slate-800/80'
      }`}
    >
      <div className="flex items-center justify-between text-xs">
        <span className="text-slate-300 font-medium">{label}</span>
        <div className="flex items-baseline gap-1">
          <span
            className={`font-mono font-bold text-sm ${
              isEvaluated
                ? highlight
                  ? 'text-emerald-300'
                  : 'text-white'
                : 'text-slate-500'
            }`}
          >
            {displayValue}
          </span>
          {unit && isEvaluated && <span className="text-[10px] text-slate-400 font-mono">{unit}</span>}
        </div>
      </div>
      <div className="text-[10px] text-slate-400 mt-0.5">{description}</div>
    </div>
  );
};
