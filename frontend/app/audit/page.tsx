'use client';

// app/audit/page.tsx — Action Audit Log Dashboard
// Observability center with full service, status, approval filtering and text search.

import { useState, useEffect } from 'react';
import { api, getBaseUrl } from '@/lib/api';
import type { AuditLog } from '@/lib/types';

const SERVICE_FILTERS = [
  { id: 'all', label: 'All Services' },
  { id: 'gmail', label: 'Gmail' },
  { id: 'calendar', label: 'Calendar' },
  { id: 'drive', label: 'Drive' },
  { id: 'system', label: 'System' },
];

const STATUS_FILTERS = [
  { id: 'all', label: 'All Statuses' },
  { id: 'approved', label: 'Approved Only' },
  { id: 'rejected', label: 'Rejected Only' },
  { id: 'failed', label: 'Failed' },
];

const STATUS_STYLE: Record<string, string> = {
  success: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
  failed: 'text-red-400 bg-red-500/10 border-red-500/30',
  skipped: 'text-slate-400 bg-slate-500/10 border-slate-500/30',
};

const ACTION_ICON: Record<string, string> = {
  read: '👁',
  write: '✏️',
  sensitive: '🔐',
  system: '⚙️',
};

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [serviceFilter, setServiceFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const serviceParam = serviceFilter === 'all' ? undefined : serviceFilter;
    const statusParam = statusFilter === 'failed' ? 'failed' : undefined;
    const approvalParam =
      statusFilter === 'approved' ? 'approved' : statusFilter === 'rejected' ? 'rejected' : undefined;

    const qs = new URLSearchParams();
    if (serviceParam) qs.set('service', serviceParam);
    if (statusParam) qs.set('status', statusParam);
    if (approvalParam) qs.set('approval_status', approvalParam);
    if (searchQuery.trim()) qs.set('q', searchQuery.trim());
    qs.set('limit', '100');

    fetch(`${getBaseUrl()}/api/audit?${qs.toString()}`)
      .then((res) => res.json())
      .then((data) => {
        setLogs(Array.isArray(data) ? data : []);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [serviceFilter, statusFilter, searchQuery]);

  return (
    <div className="flex-1 overflow-y-auto p-8">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            📋 Action Audit Log
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Complete, immutable trail of all operations executed by ORBIT 180.
          </p>
        </div>

        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs">
          <span>🛡</span>
          <span>Automatic Secret Sanitization Active</span>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="mb-6 space-y-3 bg-[#1a1d27] border border-slate-800 rounded-xl p-4">
        {/* Search */}
        <div className="flex gap-3">
          <div className="relative flex-1">
            <span className="absolute left-3 top-2.5 text-slate-500 text-sm">🔍</span>
            <input
              type="text"
              placeholder="Search tool names, summaries, or parameters..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#141720] border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 outline-none focus:border-indigo-500"
            />
          </div>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center justify-between gap-4 flex-wrap pt-2 border-t border-slate-800">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[11px] text-slate-500 font-medium mr-1">Service:</span>
            {SERVICE_FILTERS.map((f) => (
              <button
                key={f.id}
                onClick={() => setServiceFilter(f.id)}
                className={`px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors cursor-pointer ${
                  serviceFilter === f.id
                    ? 'bg-indigo-600/30 border-indigo-500 text-indigo-300'
                    : 'border-slate-700 text-slate-400 hover:border-slate-600 hover:text-white'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[11px] text-slate-500 font-medium mr-1">Outcome:</span>
            {STATUS_FILTERS.map((s) => (
              <button
                key={s.id}
                onClick={() => setStatusFilter(s.id)}
                className={`px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors cursor-pointer ${
                  statusFilter === s.id
                    ? 'bg-indigo-600/30 border-indigo-500 text-indigo-300'
                    : 'border-slate-700 text-slate-400 hover:border-slate-600 hover:text-white'
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Empty State */}
      {logs.length === 0 && !loading && (
        <div className="rounded-xl border border-slate-800 bg-[#1a1d27] p-10 text-center">
          <span className="text-3xl block mb-2">📁</span>
          <p className="text-slate-300 font-medium text-sm">No audit records matching your filters</p>
          <p className="text-slate-500 text-xs mt-1">
            Try adjusting your service or status filters above, or send requests in Chat.
          </p>
        </div>
      )}

      {/* Log Entries */}
      <div className="space-y-3">
        {logs.map((log) => (
          <div
            key={log.id}
            className="rounded-xl border border-slate-800 bg-[#1a1d27] p-4.5 hover:border-slate-700 transition-colors"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <span className="text-xl flex-shrink-0 mt-0.5" title={log.action_type}>
                  {ACTION_ICON[log.action_type] ?? '🔧'}
                </span>

                <div className="space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-white text-sm font-semibold">{log.tool_name}</span>
                    <span className="text-[10px] bg-slate-800 text-slate-400 border border-slate-700 px-2 py-0.5 rounded-full uppercase tracking-wider">
                      {log.service}
                    </span>

                    {log.approval_required && (
                      <span className="text-[10px] bg-amber-500/20 text-amber-400 border border-amber-500/40 px-2 py-0.5 rounded-full font-medium">
                        HITL Approval Required
                      </span>
                    )}

                    {log.approval_status && (
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded-full font-medium border ${
                          log.approval_status === 'approved'
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                            : 'bg-red-500/10 text-red-400 border-red-500/30'
                        }`}
                      >
                        {log.approval_status === 'approved' ? '✓ Human Approved' : '✗ Human Rejected'}
                      </span>
                    )}
                  </div>

                  {log.input_summary && (
                    <p className="text-slate-300 text-xs leading-relaxed">
                      <span className="text-slate-500 font-medium">Parameters: </span>
                      <span className="font-mono text-slate-300">{log.input_summary}</span>
                    </p>
                  )}

                  {log.result_summary && (
                    <p className="text-slate-400 text-xs leading-relaxed">
                      <span className="text-slate-500 font-medium">Output: </span>
                      {log.result_summary}
                    </p>
                  )}
                </div>
              </div>

              <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
                <span className={`text-[10px] px-2.5 py-0.5 rounded-full border font-medium ${STATUS_STYLE[log.status] ?? ''}`}>
                  {log.status}
                </span>
                <span className="text-slate-500 text-[11px] font-mono">
                  {new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
