'use client';

// app/settings/page.tsx — Settings and Google Services Connection
import { useState, useEffect } from 'react';
import { api, getBaseUrl } from '@/lib/api';

export default function SettingsPage() {
  const [loading, setLoading] = useState(true);
  const [googleConnected, setGoogleConnected] = useState(false);
  const [authMode, setAuthMode] = useState<'live' | 'demo'>('demo');
  const [geminiConfigured, setGeminiConfigured] = useState(false);
  const [googleOAuthConfigured, setGoogleOAuthConfigured] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [connectingDemo, setConnectingDemo] = useState(false);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [notification, setNotification] = useState<{ type: 'error' | 'success' | 'info'; message: string } | null>(null);

  useEffect(() => {
    // Check URL parameters for status
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      if (params.get('oauth_missing') === 'true') {
        setShowConfigModal(true);
        setNotification({
          type: 'info',
          message: 'Google Cloud OAuth keys are not configured in backend/.env yet. Follow the steps below or use Demo Mode.',
        });
      } else if (params.get('connected') === 'true' || params.get('mock_connected') === 'true') {
        setNotification({
          type: 'success',
          message: 'Google Account successfully connected!',
        });
      } else if (params.get('error')) {
        setNotification({
          type: 'error',
          message: `Connection error: ${params.get('error')}`,
        });
      }
    }

    refreshStatus();
  }, []);

  async function refreshStatus() {
    try {
      const [user, status] = await Promise.all([
        api.getMe().catch(() => null),
        api.getAuthStatus().catch(() => null),
      ]);
      if (user) {
        setGoogleConnected(Boolean(user.google_connected));
        setAuthMode(user.google_connected ? 'live' : 'demo');
      }
      if (status) {
        setGeminiConfigured(Boolean(status.gemini_configured));
        setGoogleOAuthConfigured(Boolean(status.google_oauth_configured));
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleDisconnect() {
    setDisconnecting(true);
    try {
      await fetch(`${getBaseUrl()}/api/auth/disconnect`, { method: 'POST' });
      setGoogleConnected(false);
      setAuthMode('demo');
      setNotification({ type: 'info', message: 'Google account disconnected. Switched to demo mode.' });
    } catch (e) {
      console.error(e);
      setNotification({ type: 'error', message: 'Failed to disconnect account.' });
    } finally {
      setDisconnecting(false);
    }
  }

  async function handleSimulateConnect() {
    setConnectingDemo(true);
    try {
      const res = await fetch(`${getBaseUrl()}/api/auth/simulate-connect`, { method: 'POST' });
      if (res.ok) {
        setGoogleConnected(true);
        setAuthMode('live');
        setShowConfigModal(false);
        setNotification({
          type: 'success',
          message: 'Demo Google account connected! All services (Gmail, Calendar, Drive) are now active.',
        });
      }
    } catch (e) {
      console.error(e);
      setNotification({ type: 'error', message: 'Failed to enable demo connection.' });
    } finally {
      setConnectingDemo(false);
    }
  }

  function handleConnectGoogle() {
    if (!googleOAuthConfigured) {
      setShowConfigModal(true);
    } else {
      window.location.href = `${getBaseUrl()}/api/auth/login`;
    }
  }

  return (
    <div className="flex-1 overflow-y-auto p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">⚙️ Settings</h1>
        <p className="text-slate-400 text-sm mt-1">Connected accounts and agent settings</p>
      </div>

      {notification && (
        <div
          className={`mb-6 p-4 rounded-xl text-sm border flex items-center justify-between ${
            notification.type === 'success'
              ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300'
              : notification.type === 'error'
              ? 'bg-red-950/40 border-red-500/40 text-red-300'
              : 'bg-indigo-950/40 border-indigo-500/40 text-indigo-300'
          }`}
        >
          <span>{notification.message}</span>
          <button
            onClick={() => setNotification(null)}
            className="text-xs text-slate-400 hover:text-white ml-4 cursor-pointer"
          >
            ✕
          </button>
        </div>
      )}

      <div className="max-w-2xl space-y-5">
        {/* Google Connection Card */}
        <div className="rounded-xl border border-slate-700 bg-[#1a1d27] p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-white font-semibold flex items-center gap-2">
                Google Workspace Services
                <span
                  className={`text-[10px] px-2.5 py-0.5 rounded-full font-medium border ${
                    googleConnected
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                      : 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30'
                  }`}
                >
                  {googleConnected ? '● Connected (Live Google)' : '○ Demo Mode (Simulated)'}
                </span>
              </h2>
              <p className="text-slate-400 text-xs mt-1">
                {googleConnected
                  ? 'Active access to live Gmail, Google Calendar, and Google Drive.'
                  : 'Operating in mock demo mode. Connect to query your live Google account data.'}
              </p>
            </div>
            {googleConnected ? (
              <button
                onClick={handleDisconnect}
                disabled={disconnecting}
                className="px-3 py-1.5 rounded-lg bg-red-600/20 hover:bg-red-600/30 text-red-300 border border-red-500/30 text-xs font-medium cursor-pointer"
              >
                {disconnecting ? 'Disconnecting...' : 'Disconnect'}
              </button>
            ) : (
              <button
                onClick={handleConnectGoogle}
                className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold cursor-pointer shadow-md transition-all"
              >
                Connect Google Account
              </button>
            )}
          </div>

          <div className="divide-y divide-slate-800">
            {[
              { name: 'Gmail', icon: '✉️', desc: 'Read inbox, create drafts, send emails with human approval' },
              { name: 'Google Calendar', icon: '📅', desc: 'Query schedule, inspect free time, schedule meetings' },
              { name: 'Google Drive', icon: '📁', desc: 'Search documents, read lecture notes, locate project reports' },
            ].map((s) => (
              <div key={s.name} className="flex items-center justify-between py-3">
                <div className="flex items-center gap-3">
                  <span className="text-xl">{s.icon}</span>
                  <div>
                    <p className="text-white text-sm font-medium">{s.name}</p>
                    <p className="text-slate-500 text-xs">{s.desc}</p>
                  </div>
                </div>
                <span
                  className={`text-[11px] px-2.5 py-0.5 rounded-full ${
                    googleConnected ? 'text-emerald-400 bg-emerald-500/10' : 'text-slate-400 bg-slate-800'
                  }`}
                >
                  {googleConnected ? 'Active' : 'Ready (Demo)'}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* AI Configuration */}
        <div className="rounded-xl border border-slate-700 bg-[#1a1d27] p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-white font-semibold">Gemini AI Model</h2>
            <span
              className={`text-[10px] px-2.5 py-0.5 rounded-full font-medium border ${
                geminiConfigured
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                  : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
              }`}
            >
              {geminiConfigured ? '✓ Configured' : '⚠ Using Agent Synthesizer'}
            </span>
          </div>
          <div className="space-y-2 text-xs text-slate-400">
            <p>
              To enable live Gemini reasoning, set{' '}
              <code className="bg-slate-800 text-indigo-300 px-1 rounded text-xs">GEMINI_API_KEY</code> in{' '}
              <code className="bg-slate-800 text-indigo-300 px-1 rounded text-xs">backend/.env</code>.
            </p>
            <p>
              Get your free key with no credit card at{' '}
              <a
                href="https://aistudio.google.com/apikey"
                target="_blank"
                rel="noreferrer"
                className="text-indigo-400 hover:underline"
              >
                aistudio.google.com/apikey ↗
              </a>
            </p>
          </div>
        </div>
      </div>

      {/* OAuth Configuration / Demo Connect Modal */}
      {showConfigModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#1a1d27] border border-slate-700 rounded-2xl p-6 max-w-lg w-full shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-white font-bold text-base flex items-center gap-2">
                <span>🔑</span> Google OAuth Credentials Setup
              </h3>
              <button
                onClick={() => setShowConfigModal(false)}
                className="text-slate-400 hover:text-white text-sm cursor-pointer"
              >
                ✕
              </button>
            </div>

            <p className="text-slate-300 text-xs leading-relaxed">
              To connect your <strong>real Google Account</strong>, Google requires OAuth API credentials created in the
              Google Cloud Console.
            </p>

            <div className="bg-[#0f1117] border border-slate-800 rounded-xl p-3 text-xs space-y-2">
              <p className="text-indigo-300 font-semibold">Option A: Connect with Real Google Account</p>
              <ol className="list-decimal list-inside text-slate-400 space-y-1">
                <li>Go to <a href="https://console.cloud.google.com/" target="_blank" rel="noreferrer" className="text-indigo-400 underline">Google Cloud Console ↗</a></li>
                <li>Create an OAuth Client ID (Web Application)</li>
                <li>Add redirect URI: <code className="text-slate-300 bg-slate-800 px-1 rounded">http://localhost:8000/api/auth/callback</code></li>
                <li>Paste credentials into <code className="text-slate-300 bg-slate-800 px-1 rounded">backend/.env</code>:</li>
              </ol>
              <pre className="bg-slate-900 p-2 rounded text-[11px] text-slate-300 font-mono overflow-x-auto">
{`GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret`}
              </pre>
            </div>

            <div className="bg-[#0f1117] border border-slate-800 rounded-xl p-3 text-xs space-y-2">
              <p className="text-emerald-400 font-semibold">Option B: Instant Simulated Connection (Demo Mode)</p>
              <p className="text-slate-400">
                You can activate a simulated connected Google account right now without creating Google Cloud keys.
              </p>
              <button
                onClick={handleSimulateConnect}
                disabled={connectingDemo}
                className="w-full py-2 px-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs cursor-pointer transition-all"
              >
                {connectingDemo ? 'Connecting...' : '⚡ Connect Simulated Google Account Now'}
              </button>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setShowConfigModal(false)}
                className="px-4 py-1.5 text-xs text-slate-400 hover:text-white cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
