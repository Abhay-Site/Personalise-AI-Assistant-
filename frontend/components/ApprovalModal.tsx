'use client';

// components/ApprovalModal.tsx — Comprehensive Human-in-the-Loop modal dialog
// Allows the user to inspect, edit, approve, or reject sensitive operations.

import { useState } from 'react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  actionPlanId: number;
  actionType: string;
  description?: string;
  initialArgs?: Record<string, any>;
  onDecision: (approved: boolean, editedAction?: Record<string, any>) => Promise<void>;
}

export function ApprovalModal({
  isOpen,
  onClose,
  actionPlanId,
  actionType,
  description,
  initialArgs = {},
  onDecision,
}: Props) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedTo, setEditedTo] = useState(String(initialArgs?.to || ''));
  const [editedSubject, setEditedSubject] = useState(String(initialArgs?.subject || ''));
  const [editedBody, setEditedBody] = useState(String(initialArgs?.body || ''));
  const [submitting, setSubmitting] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  if (!isOpen) return null;

  async function handleAction(approved: boolean) {
    setSubmitting(true);
    setModalError(null);
    let editedPayload: Record<string, any> | undefined = undefined;

    if (approved && isEditing) {
      editedPayload = {
        ...initialArgs,
        to: editedTo,
        subject: editedSubject,
        body: editedBody,
      };
    }

    try {
      await onDecision(approved, editedPayload);
      onClose();
    } catch (err) {
      setModalError(err instanceof Error ? err.message : 'Action execution failed');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-in fade-in duration-150">
      <div className="w-full max-w-lg rounded-2xl border border-slate-700 bg-[#1a1d27] shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-amber-500/10">
          <div className="flex items-center gap-2.5">
            <span className="text-xl">⚠️</span>
            <div>
              <h2 className="text-base font-bold text-white leading-tight">
                Action Requires Explicit Approval
              </h2>
              <p className="text-slate-400 text-xs mt-0.5">Plan #{actionPlanId} • Security Policy</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-500 hover:text-white text-lg p-1"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-4 flex-1">
          <div className="rounded-xl border border-slate-800 bg-[#141720] p-4">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-semibold text-amber-400 uppercase tracking-wider">
                Operation
              </span>
              <span className="text-[10px] bg-amber-500/20 text-amber-400 border border-amber-500/30 px-2 py-0.5 rounded-full font-mono">
                SENSITIVE
              </span>
            </div>
            <p className="text-white font-medium text-sm">{actionType}</p>
            {description && <p className="text-slate-400 text-xs mt-1">{description}</p>}
          </div>

          {modalError && (
            <div className="rounded-xl border border-red-500/40 bg-red-500/15 p-3 text-xs text-red-200 flex items-start gap-2 shadow-sm">
              <span className="text-sm leading-none mt-0.5">⚠️</span>
              <div className="flex-1">
                <span className="font-semibold text-red-100">Execution Error: </span>
                <span>{modalError}</span>
              </div>
            </div>
          )}

          {/* Parameters View or Edit */}
          {!isEditing ? (
            <div className="rounded-xl border border-slate-800 bg-[#141720] p-4 space-y-2 text-xs">
              <div className="flex items-center justify-between mb-1">
                <span className="text-slate-400 font-medium">Staged Parameters</span>
                <button
                  onClick={() => setIsEditing(true)}
                  className="text-indigo-400 hover:text-indigo-300 font-medium cursor-pointer"
                >
                  ✏️ Edit Details
                </button>
              </div>

              {initialArgs?.to && (
                <div>
                  <span className="text-slate-500">Recipients: </span>
                  <span className="text-slate-200 font-mono">{String(initialArgs.to)}</span>
                </div>
              )}
              {initialArgs?.subject && (
                <div>
                  <span className="text-slate-500">Subject: </span>
                  <span className="text-slate-200">{String(initialArgs.subject)}</span>
                </div>
              )}
              {initialArgs?.body && (
                <div className="pt-1">
                  <span className="text-slate-500 block mb-1">Body Preview:</span>
                  <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 whitespace-pre-wrap font-sans text-[11px] max-h-32 overflow-y-auto">
                    {String(initialArgs.body)}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-3 rounded-xl border border-indigo-500/30 bg-indigo-500/5 p-4 text-xs">
              <div className="flex items-center justify-between mb-1">
                <span className="text-indigo-300 font-medium">Editing Parameters</span>
                <button
                  onClick={() => setIsEditing(false)}
                  className="text-slate-400 hover:text-white"
                >
                  Cancel Edit
                </button>
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Recipients (To)</label>
                <input
                  type="text"
                  value={editedTo}
                  onChange={(e) => setEditedTo(e.target.value)}
                  className="w-full bg-[#141720] border border-slate-700 rounded-lg px-3 py-1.5 text-white outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Subject</label>
                <input
                  type="text"
                  value={editedSubject}
                  onChange={(e) => setEditedSubject(e.target.value)}
                  className="w-full bg-[#141720] border border-slate-700 rounded-lg px-3 py-1.5 text-white outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Email Body</label>
                <textarea
                  rows={4}
                  value={editedBody}
                  onChange={(e) => setEditedBody(e.target.value)}
                  className="w-full bg-[#141720] border border-slate-700 rounded-lg px-3 py-1.5 text-white outline-none focus:border-indigo-500 resize-none"
                />
              </div>
            </div>
          )}

          <p className="text-[11px] text-slate-500 italic text-center">
            ORBIT 180 will only execute this action if you confirm. Rejecting will safely abort without modifying data.
          </p>
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 border-t border-slate-800 bg-[#141720] flex items-center justify-between gap-3">
          <button
            onClick={() => handleAction(false)}
            disabled={submitting}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold cursor-pointer border border-slate-700 transition-colors"
          >
            ✗ Reject Action
          </button>

          <button
            onClick={() => handleAction(true)}
            disabled={submitting}
            className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold cursor-pointer shadow-lg transition-colors flex items-center gap-1.5"
          >
            {submitting ? 'Executing...' : isEditing ? '✓ Approve with Edits' : '✓ Approve & Dispatch'}
          </button>
        </div>
      </div>
    </div>
  );
}
