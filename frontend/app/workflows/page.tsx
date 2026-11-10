'use client';

// app/workflows/page.tsx — Cross-application & Student Workflows Hub
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

interface WorkflowTemplate {
  id: string;
  title: string;
  category: string;
  icon: string;
  description: string;
  prompt: string;
  services: string[];
}

interface WorkflowHistoryItem {
  id: number;
  conversation_id: number;
  goal: string;
  steps_count: number;
  status: string;
  created_at: string;
}

import { getBaseUrl } from '@/lib/api';

export default function WorkflowsPage() {
  const router = useRouter();
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [history, setHistory] = useState<WorkflowHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [runningId, setRunningId] = useState<string | null>(null);

  useEffect(() => {
    const baseUrl = getBaseUrl();
    Promise.all([
      fetch(`${baseUrl}/api/workflows`).then((r) => r.json()).catch(() => []),
      fetch(`${baseUrl}/api/workflows/history`).then((r) => r.json()).catch(() => []),
    ]).then(([tmpl, hist]) => {
      setTemplates(tmpl);
      setHistory(hist);
      setLoading(false);
    });
  }, []);

  function handleLaunchWorkflow(prompt: string) {
    // Navigate to chat with prompt pre-filled via sessionStorage or query
    if (typeof window !== 'undefined') {
      sessionStorage.setItem('assistant_initial_prompt', prompt);
    }
    router.push('/chat');
  }

  return (
    <div className="flex-1 overflow-y-auto p-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          ⚡ Workflows & Automation
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Execute end-to-end multi-step tasks across Gmail, Calendar, and Drive with one click.
        </p>
      </div>

      {/* Available Templates */}
      <div className="mb-10">
        <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4">
          Featured Workflows
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {templates.map((w) => (
            <div
              key={w.id}
              className="rounded-xl border border-slate-700 bg-[#1a1d27] p-5 flex flex-col justify-between hover:border-indigo-500/40 transition-all"
            >
              <div>
                <div className="flex items-start justify-between mb-3">
                  <span className="text-3xl">{w.icon}</span>
                  <div className="flex gap-1">
                    {w.services.map((s) => (
                      <span
                        key={s}
                        className="text-[9px] bg-slate-800 text-slate-400 border border-slate-700 px-2 py-0.5 rounded-full capitalize"
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                </div>

                <h3 className="text-white font-semibold text-base mb-1.5">{w.title}</h3>
                <p className="text-slate-400 text-xs leading-relaxed mb-4">{w.description}</p>
              </div>

              <button
                onClick={() => handleLaunchWorkflow(w.prompt)}
                className="w-full py-2 px-3 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium cursor-pointer transition-colors flex items-center justify-center gap-1.5"
              >
                <span>Run in Chat</span>
                <span>→</span>
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Workflow Execution History */}
      <div>
        <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4">
          Recent Workflow Executions
        </h2>

        {history.length === 0 && !loading && (
          <div className="rounded-xl border border-slate-800 bg-[#141720] p-6 text-center text-slate-500 text-xs">
            No workflows executed yet. Launch a workflow above or chat with Personal AI Assistant to generate an action plan.
          </div>
        )}

        <div className="space-y-2.5">
          {history.map((h) => (
            <div
              key={h.id}
              className="rounded-xl border border-slate-800 bg-[#1a1d27] px-4 py-3 flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                <span className="text-indigo-400 font-mono text-xs">#{h.id}</span>
                <div>
                  <p className="text-slate-200 text-sm font-medium">{h.goal}</p>
                  <p className="text-slate-500 text-[11px]">{h.steps_count} steps planned</p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <span
                  className={`text-[10px] px-2.5 py-0.5 rounded-full font-medium border ${
                    h.status === 'executed'
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                      : h.status === 'rejected'
                      ? 'bg-red-500/10 text-red-400 border-red-500/30'
                      : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                  }`}
                >
                  {h.status}
                </span>
                <span className="text-slate-500 text-xs">
                  {new Date(h.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
