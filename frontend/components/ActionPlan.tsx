// ActionPlan.tsx — Displays the structured action plan as a human-readable card

import type { ActionPlan, ActionStep } from '@/lib/types';

const SERVICE_ICONS: Record<string, string> = {
  gmail:    '✉️',
  calendar: '📅',
  drive:    '📁',
  system:   '⚙️',
};

const STATUS_STYLE: Record<string, string> = {
  pending:           'bg-slate-700 text-slate-400',
  running:           'bg-blue-600/30 text-blue-400',
  done:              'bg-emerald-600/30 text-emerald-400',
  failed:            'bg-red-600/30 text-red-400',
  awaiting_approval: 'bg-amber-600/30 text-amber-400',
};

function StepRow({ step }: { step: ActionStep }) {
  const icon = SERVICE_ICONS[step.service] ?? '🔧';
  const statusStyle = STATUS_STYLE[step.status] ?? STATUS_STYLE.pending;

  return (
    <div className="flex items-center gap-3 py-2">
      <div className="w-6 h-6 rounded-full bg-slate-700 flex items-center justify-center text-[10px] text-slate-400 font-mono flex-shrink-0">
        {step.order}
      </div>
      <span className="text-sm">{icon}</span>
      <div className="flex-1">
        <span className="text-xs font-medium text-slate-300 uppercase tracking-wide">{step.service}</span>
        <span className="text-slate-500 text-xs mx-1">→</span>
        <span className="text-xs text-slate-200">{step.action}</span>
        {step.description && (
          <p className="text-[10px] text-slate-500 mt-0.5">{step.description}</p>
        )}
      </div>
      {step.requires_approval && (
        <span className="text-[10px] bg-amber-500/20 text-amber-400 border border-amber-500/30 px-2 py-0.5 rounded-full">
          approval
        </span>
      )}
      <span className={`text-[10px] px-2 py-0.5 rounded-full ${statusStyle}`}>
        {step.status}
      </span>
    </div>
  );
}

export function ActionPlanCard({ plan }: { plan: ActionPlan }) {
  return (
    <div className="rounded-xl border border-slate-700 bg-[#141720] overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-800">
        <p className="text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-1">📋 Action Plan</p>
        <p className="text-sm text-slate-300">{plan.goal}</p>
      </div>
      <div className="px-4 divide-y divide-slate-800">
        {plan.steps.map((step) => (
          <StepRow key={step.order} step={step} />
        ))}
      </div>
    </div>
  );
}
