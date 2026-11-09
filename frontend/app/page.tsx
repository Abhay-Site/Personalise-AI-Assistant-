'use client';

// app/page.tsx — Executive Dashboard & Proactive Morning Briefing
import { useState, useEffect } from 'react';
import Link from 'next/link';

interface BriefingData {
  date: string;
  greeting: string;
  ai_summary: string;
  events: Array<{ id: string; summary: string; start: string; end?: string; attendees?: string[]; location?: string }>;
  important_emails: Array<{ id: string; subject: string; from: string; date?: string; snippet?: string }>;
  recommended_files: Array<{ id: string; name: string; link?: string; modified_time?: string }>;
  conflicts: Array<{ event_a: string; event_b: string; time: string; reason: string; suggestion: string }>;
  stats: {
    events_count: number;
    emails_count: number;
    files_count: number;
    conflicts_count: number;
  };
}

import { getBaseUrl } from '@/lib/api';

export default function DashboardPage() {
  const [briefing, setBriefing] = useState<BriefingData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${getBaseUrl()}/api/briefing`)
      .then((res) => res.json())
      .then((data) => setBriefing(data))
      .catch((err) => console.error('Failed to load briefing:', err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex-1 overflow-y-auto p-8">
      {/* Header */}
      <div className="flex items-start justify-between mb-8 flex-wrap gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-white mb-1.5 flex items-center gap-2">
            <span>☀️</span>
            <span>{briefing ? briefing.greeting : 'Good morning!'}</span>
          </h1>
          <p className="text-slate-400 text-sm">
            {briefing?.date || 'Your unified cross-application productivity briefing'}
          </p>
        </div>

        <Link
          href="/workflows"
          className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-lg shadow-indigo-600/20 transition-all flex items-center gap-2"
        >
          <span>⚡ Launch Student Workflows</span>
          <span>→</span>
        </Link>
      </div>

      {/* Schedule Conflict Alert Banner (Section 4.5 & 22) */}
      {briefing && briefing.conflicts && briefing.conflicts.length > 0 && (
        <div className="mb-6 rounded-xl border border-red-500/40 bg-red-500/10 p-4.5 animate-in fade-in">
          <div className="flex items-start gap-3">
            <span className="text-2xl mt-0.5">⚠️</span>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <h3 className="text-red-300 font-bold text-sm">Schedule Conflict Detected</h3>
                <span className="text-[10px] bg-red-500/20 text-red-400 border border-red-500/40 px-2 py-0.5 rounded-full font-mono uppercase">
                  Action Required
                </span>
              </div>
              {briefing.conflicts.map((c, i) => (
                <div key={i} className="text-xs text-slate-300 space-y-1 mt-1.5">
                  <p>{c.reason}</p>
                  <p className="text-amber-400 font-medium">💡 Recommendation: {c.suggestion}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* KPI Stats Overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard
          icon="📅"
          label="Today's Events"
          value={briefing?.stats.events_count ?? 2}
          detail="Classes & Meetings"
          accent="indigo"
          targetId="schedule-section"
        />
        <StatCard
          icon="📬"
          label="Actionable Emails"
          value={briefing?.stats.emails_count ?? 2}
          detail="Deadlines & Notices"
          accent="purple"
          targetId="emails-section"
        />
        <StatCard
          icon="📁"
          label="Relevant Files"
          value={briefing?.stats.files_count ?? 3}
          detail="In Google Drive"
          accent="emerald"
          targetId="files-section"
        />
        <StatCard
          icon="⚠️"
          label="Schedule Clashes"
          value={briefing?.stats.conflicts_count ?? 0}
          detail={briefing?.stats.conflicts_count ? 'Conflicts Flagged' : 'Schedule Clear'}
          accent={briefing?.stats.conflicts_count ? 'red' : 'emerald'}
          targetId="conflicts-section"
        />
      </div>

      {/* Quick Navigation Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <QuickCard
          icon="💬"
          title="Cross-App Chat"
          desc="Ask natural-language questions across Gmail, Calendar & Drive"
          href="/chat"
          accent="indigo"
        />
        <QuickCard
          icon="🧠"
          title="User Preferences"
          desc="Manage memory, study hours, and automated planning rules"
          href="/memory"
          accent="purple"
        />
        <QuickCard
          icon="📋"
          title="Security & Audit"
          desc="Inspect the complete sanitized execution log with secret redaction"
          href="/audit"
          accent="emerald"
        />
      </div>

      {/* Unified Morning Briefing Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 1. Schedule Agenda */}
        <div id="schedule-section" className="rounded-xl border border-slate-800 bg-[#1a1d27] p-5 flex flex-col scroll-mt-6">
          <h2 className="text-white font-semibold text-sm mb-4 flex items-center justify-between">
            <span className="flex items-center gap-2">📅 Schedule for Today</span>
            <span className="text-[11px] text-slate-500 font-normal">Google Calendar</span>
          </h2>

          <div className="space-y-3 flex-1">
            {briefing?.events && briefing.events.length > 0 ? (
              briefing.events.map((evt) => (
                <div key={evt.id} className="p-3 rounded-xl bg-[#141720] border border-slate-800/80">
                  <p className="text-white text-xs font-semibold">{evt.summary}</p>
                  <p className="text-indigo-400 text-[11px] font-mono mt-0.5">{evt.start}</p>
                  {evt.location && <p className="text-slate-500 text-[10px] mt-0.5">📍 {evt.location}</p>}
                </div>
              ))
            ) : (
              <p className="text-slate-500 text-xs italic">No events scheduled today.</p>
            )}
          </div>
        </div>

        {/* 2. Priority Emails */}
        <div id="emails-section" className="rounded-xl border border-slate-800 bg-[#1a1d27] p-5 flex flex-col scroll-mt-6">
          <h2 className="text-white font-semibold text-sm mb-4 flex items-center justify-between">
            <span className="flex items-center gap-2">📬 Important Messages</span>
            <span className="text-[11px] text-slate-500 font-normal">Gmail</span>
          </h2>

          <div className="space-y-3 flex-1">
            {briefing?.important_emails && briefing.important_emails.length > 0 ? (
              briefing.important_emails.map((msg) => (
                <div key={msg.id} className="p-3 rounded-xl bg-[#141720] border border-slate-800/80">
                  <p className="text-white text-xs font-semibold truncate">{msg.subject}</p>
                  <p className="text-slate-400 text-[11px] truncate">{msg.from}</p>
                  {msg.snippet && (
                    <p className="text-slate-500 text-[10px] line-clamp-2 mt-1 leading-relaxed">
                      {msg.snippet}
                    </p>
                  )}
                </div>
              ))
            ) : (
              <p className="text-slate-500 text-xs italic">Inbox is clear of priority announcements.</p>
            )}
          </div>
        </div>

        {/* 3. Recommended Drive Materials */}
        <div id="files-section" className="rounded-xl border border-slate-800 bg-[#1a1d27] p-5 flex flex-col scroll-mt-6">
          <h2 className="text-white font-semibold text-sm mb-4 flex items-center justify-between">
            <span className="flex items-center gap-2">📁 Materials & Files</span>
            <span className="text-[11px] text-slate-500 font-normal">Google Drive</span>
          </h2>

          <div className="space-y-3 flex-1">
            {briefing?.recommended_files && briefing.recommended_files.length > 0 ? (
              briefing.recommended_files.map((file) => (
                <div key={file.id} className="p-3 rounded-xl bg-[#141720] border border-slate-800/80 flex items-center justify-between">
                  <div className="min-w-0 pr-2">
                    <p className="text-white text-xs font-semibold truncate">{file.name}</p>
                    <p className="text-slate-500 text-[10px]">{file.modified_time || 'Recent'}</p>
                  </div>
                  {file.link && (
                    <a
                      href={file.link}
                      target="_blank"
                      rel="noreferrer"
                      className="text-indigo-400 hover:text-indigo-300 text-xs px-2 py-1 bg-indigo-500/10 rounded-lg flex-shrink-0"
                    >
                      View ↗
                    </a>
                  )}
                </div>
              ))
            ) : (
              <p className="text-slate-500 text-xs italic">No recently accessed documents.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({
  icon, label, value, detail, accent, targetId,
}: {
  icon: string; label: string; value: number; detail: string; accent: string; targetId?: string;
}) {
  const accentBorder: Record<string, string> = {
    indigo: 'border-indigo-500/20 text-indigo-400 hover:border-indigo-500/50',
    purple: 'border-purple-500/20 text-purple-400 hover:border-purple-500/50',
    emerald: 'border-emerald-500/20 text-emerald-400 hover:border-emerald-500/50',
    red: 'border-red-500/30 text-red-400 hover:border-red-500/50',
  };

  const handleClick = () => {
    if (targetId) {
      const el = document.getElementById(targetId);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  };

  return (
    <div
      onClick={handleClick}
      className={`rounded-xl border bg-[#1a1d27] hover:bg-[#202538] p-4.5 cursor-pointer transition-all hover:scale-[1.03] shadow-sm ${accentBorder[accent] ?? accentBorder.indigo}`}
      title={`Click to view ${label}`}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-xl">{icon}</span>
        <span className="text-2xl font-extrabold text-white">{value}</span>
      </div>
      <p className="text-white text-xs font-semibold flex items-center justify-between">
        <span>{label}</span>
        <span className="text-[10px] text-slate-500 font-normal">View ↓</span>
      </p>
      <p className="text-slate-500 text-[10px] mt-0.5">{detail}</p>
    </div>
  );
}

function QuickCard({
  icon, title, desc, href, accent,
}: {
  icon: string; title: string; desc: string; href: string; accent: string;
}) {
  return (
    <Link
      href={href}
      className="block rounded-xl border border-slate-800 hover:border-indigo-500/40 bg-[#1a1d27] hover:bg-[#1f2333] p-5 cursor-pointer transition-all"
    >
      <div className="text-2xl mb-2.5">{icon}</div>
      <h3 className="font-semibold text-white text-sm mb-1">{title}</h3>
      <p className="text-xs text-slate-400 leading-relaxed">{desc}</p>
    </Link>
  );
}
