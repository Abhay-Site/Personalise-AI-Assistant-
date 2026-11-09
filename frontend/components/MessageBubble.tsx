'use client';

import { useState, useMemo } from 'react';
import type { Message, TraceStep } from '@/lib/types';
import { api } from '@/lib/api';
import { ExecutionTrace } from './ExecutionTrace';
import { ActionPlanCard } from './ActionPlan';
import { ApprovalModal } from './ApprovalModal';

interface Props {
  message: Message;
}

export function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user';
  const [decision, setDecision] = useState<'idle' | 'approving' | 'approved' | 'rejecting' | 'rejected'>('idle');
  const [feedback, setFeedback] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  async function handleDecision(approved: boolean, editedAction?: Record<string, any>) {
    if (!message.action_plan_id) return;
    setDecision(approved ? 'approving' : 'rejecting');
    setErrorMessage(null);
    try {
      const res = await api.handleApproval({
        action_plan_id: message.action_plan_id,
        approved,
        edited_action: editedAction,
      });
      setDecision(approved ? 'approved' : 'rejected');
      setFeedback(res.message);
    } catch (err) {
      setDecision('idle');
      const errText = err instanceof Error ? err.message : 'Action failed';
      setErrorMessage(errText);
      throw err;
    }
  }

  const approvalAction = message.approval_action;
  const initialArgs = (approvalAction?.args as Record<string, any>) || {};

  // Dynamically update the action plan card when approved
  const displayPlan = useMemo(() => {
    if (!message.action_plan) return null;
    if (decision !== 'approved') return message.action_plan;
    return {
      ...message.action_plan,
      steps: message.action_plan.steps.map((s) => ({
        ...s,
        status: s.requires_approval ? 'done' : s.status,
      })),
    };
  }, [message.action_plan, decision]);

  // Dynamically update the execution trace when approved
  const displayTrace = useMemo((): TraceStep[] => {
    if (!message.trace) return [];
    if (decision !== 'approved') return message.trace;
    return message.trace.map((t): TraceStep => {
      if (t.message.toLowerCase().includes('paused') || t.status === 'warning') {
        return {
          status: 'ok',
          message: `✓ Unpaused: 'send_email' approved and executed successfully`,
          detail: 'User approved execution.',
        };
      }
      return t;
    });
  }, [message.trace, decision]);

  return (
    <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} gap-2 w-full`}>
      {/* Role and Model Integration label */}
      <div className="flex items-center gap-2 px-1 flex-wrap">
        <span className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">
          {isUser ? 'You' : '🤖 ORBIT 180'}
        </span>
        {!isUser && message.model_name && !message.is_fallback && (
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-medium flex items-center gap-1 shadow-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            <span>{message.model_name}</span>
          </span>
        )}
        {!isUser && message.is_fallback && (
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/30 font-medium flex items-center gap-1 shadow-sm">
            <span>⚠</span>
            <span>{message.integration_status === 'demo' ? 'Demo Mode (Simulated AI)' : 'Local Fallback'}</span>
          </span>
        )}
      </div>

      {/* Meaningful AI Integration Error Notice */}
      {!isUser && message.is_fallback && message.error_detail && (
        <div className="max-w-[80%] rounded-xl px-3.5 py-2.5 bg-amber-500/10 border border-amber-500/30 text-xs text-amber-300 flex items-start gap-2.5 shadow-sm">
          <span className="text-sm leading-none mt-0.5">⚠️</span>
          <div className="flex-1 leading-normal">
            <span className="font-semibold text-amber-200">AI Integration Notice: </span>
            <span className="text-amber-300/90">{message.error_detail}</span>
          </div>
        </div>
      )}

      {/* Bubble */}
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
          isUser
            ? 'bg-indigo-600 text-white rounded-tr-none'
            : 'bg-[#1e2130] text-slate-200 border border-slate-700 rounded-tl-none'
        }`}
      >
        {message.content}
      </div>

      {/* Action plan (assistant only) */}
      {!isUser && displayPlan && (
        <div className="max-w-[80%] w-full">
          <ActionPlanCard plan={displayPlan} />
        </div>
      )}

      {/* Interactive Human-in-the-loop Approval Card */}
      {!isUser && message.requires_approval && approvalAction && (
        <div className="max-w-[80%] w-full rounded-xl border border-amber-500/40 bg-amber-500/10 p-4 transition-all">
          <div className="flex items-center justify-between mb-2">
            <p className="text-amber-400 font-semibold text-sm">⚠ Action Requires Your Approval</p>
            {decision === 'approved' && (
              <span className="text-[11px] bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 px-2.5 py-0.5 rounded-full font-medium">
                ✓ Approved & Executed
              </span>
            )}
            {decision === 'rejected' && (
              <span className="text-[11px] bg-red-500/20 text-red-400 border border-red-500/40 px-2.5 py-0.5 rounded-full font-medium">
                ✗ Rejected
              </span>
            )}
          </div>

          <p className="text-slate-300 text-sm">
            <span className="font-semibold text-white">{String(approvalAction.type)}</span>
            {approvalAction.description ? ` — ${String(approvalAction.description)}` : ''}
          </p>

          {/* Staged Parameter Summary for Quick Review */}
          {(initialArgs.to || initialArgs.subject) && (
            <div className="mt-2.5 p-2.5 rounded-lg bg-black/30 border border-amber-500/20 text-xs space-y-1">
              {initialArgs.to && (
                <div className="flex items-center gap-1.5 text-slate-300">
                  <span className="text-slate-400 font-medium">To:</span>
                  <span className="text-indigo-300 font-mono text-[11px]">{String(initialArgs.to)}</span>
                </div>
              )}
              {initialArgs.subject && (
                <div className="flex items-center gap-1.5 text-slate-300">
                  <span className="text-slate-400 font-medium">Subject:</span>
                  <span className="text-white">{String(initialArgs.subject)}</span>
                </div>
              )}
              {initialArgs.body && (
                <div className="pt-1 text-[11px] text-slate-400 line-clamp-2">
                  <span className="text-slate-500 font-medium">Preview: </span>
                  {String(initialArgs.body).replace(/\n+/g, ' ')}
                </div>
              )}
            </div>
          )}

          {errorMessage && (
            <div className="mt-2.5 p-2.5 rounded-lg bg-red-500/15 border border-red-500/40 text-xs text-red-200 flex items-start gap-2 shadow-sm">
              <span className="text-sm leading-none mt-0.5">⚠️</span>
              <div className="flex-1">
                <span className="font-semibold text-red-100">Approval Error: </span>
                <span>{errorMessage}</span>
              </div>
            </div>
          )}

          {feedback && !errorMessage && (
            <p className={`text-xs mt-2 font-medium ${decision === 'approved' ? 'text-emerald-400' : 'text-slate-400'}`}>
              {feedback}
            </p>
          )}

          {decision === 'idle' && (
            <div className="flex items-center gap-2 mt-3 flex-wrap">
              <button
                onClick={() => handleDecision(true)}
                disabled={decision !== 'idle'}
                className="px-5 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-white text-xs font-bold cursor-pointer transition-all shadow-lg shadow-emerald-500/30 flex items-center gap-1.5 hover:scale-105 active:scale-95"
              >
                <span>⚡</span>
                <span>Approve & Send Now</span>
              </button>
              <button
                onClick={() => setModalOpen(true)}
                className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-600 text-xs font-medium cursor-pointer transition-colors"
              >
                ✏️ Review & Edit
              </button>
              <button
                onClick={() => handleDecision(false)}
                disabled={decision !== 'idle'}
                className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-red-400 border border-red-500/20 text-xs font-medium cursor-pointer transition-colors"
              >
                ✗ Reject
              </button>
            </div>
          )}

          {(decision === 'approving' || decision === 'rejecting') && (
            <div className="flex items-center gap-2 mt-3 text-xs text-slate-400">
              <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
              Processing your decision...
            </div>
          )}

          {/* Full Approval Modal */}
          {message.action_plan_id && (
            <ApprovalModal
              isOpen={modalOpen}
              onClose={() => setModalOpen(false)}
              actionPlanId={message.action_plan_id}
              actionType={String(approvalAction.type)}
              description={String(approvalAction.description || '')}
              initialArgs={initialArgs}
              onDecision={handleDecision}
            />
          )}
        </div>
      )}

      {/* Execution trace (assistant only) */}
      {!isUser && displayTrace && displayTrace.length > 0 && (
        <div className="max-w-[80%] w-full">
          <ExecutionTrace steps={displayTrace} />
        </div>
      )}
    </div>
  );
}
