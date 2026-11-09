// ExecutionTrace.tsx — Shows the step-by-step agent execution trace
// Each step has a status (ok/warning/error) and a human-readable message.

import type { TraceStep } from '@/lib/types';
import { useState } from 'react';

interface Props {
  steps: TraceStep[];
}

const STATUS_CONFIG = {
  ok:      { icon: '✓', color: 'text-emerald-400', bg: 'bg-emerald-400' },
  warning: { icon: '⚠', color: 'text-amber-400',   bg: 'bg-amber-400'   },
  error:   { icon: '✗', color: 'text-red-400',      bg: 'bg-red-400'     },
  pending: { icon: '○', color: 'text-slate-400',    bg: 'bg-slate-400'   },
};

export function ExecutionTrace({ steps }: Props) {
  const [expanded, setExpanded] = useState(false);

  if (steps.length === 0) return null;

  const hasWarningOrError = steps.some(s => s.status === 'warning' || s.status === 'error');

  return (
    <div className="rounded-xl border border-slate-700 bg-[#141720] overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-slate-800/40 text-left"
      >
        <span className="text-xs font-medium text-slate-400 flex items-center gap-2">
          <span className={hasWarningOrError ? 'text-amber-400' : 'text-emerald-400'}>
            {hasWarningOrError ? '⚠' : '✓'}
          </span>
          Execution Trace ({steps.length} steps)
        </span>
        <span className="text-slate-600 text-xs">{expanded ? '▲' : '▼'}</span>
      </button>

      {/* Steps */}
      {expanded && (
        <div className="px-4 pb-3 space-y-2 border-t border-slate-800">
          {steps.map((step, i) => {
            const cfg = STATUS_CONFIG[step.status] ?? STATUS_CONFIG.ok;
            return (
              <div key={i} className="flex items-start gap-3 pt-2">
                <span className={`text-xs font-mono mt-0.5 ${cfg.color}`}>{cfg.icon}</span>
                <div className="flex-1">
                  <p className="text-xs text-slate-300">{step.message}</p>
                  {step.detail && (
                    <p className="text-[10px] text-slate-500 mt-0.5">{step.detail}</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
