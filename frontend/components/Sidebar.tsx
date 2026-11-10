'use client';

// Sidebar.tsx — Left navigation panel for Personal AI Assistant
// Shows app logo, nav links, and current user profile with direct edit capability

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { getBaseUrl } from '@/lib/api';

const NAV_ITEMS = [
  { href: '/',          icon: '🏠', label: 'Dashboard'  },
  { href: '/chat',      icon: '💬', label: 'Chat'        },
  { href: '/memory',    icon: '🧠', label: 'Memory'      },
  { href: '/workflows', icon: '⚡', label: 'Workflows'   },
  { href: '/audit',     icon: '📋', label: 'Audit Log'   },
  { href: '/settings',  icon: '⚙️', label: 'Settings'    },
];

export function Sidebar() {
  const pathname = usePathname();
  const [user, setUser] = useState<{ name: string; email: string }>({
    name: 'Demo User',
    email: 'demo@assistant.dev',
  });
  const [showModal, setShowModal] = useState(false);
  const [nameInput, setNameInput] = useState('');
  const [emailInput, setEmailInput] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    refreshUser();
  }, []);

  async function refreshUser() {
    try {
      const res = await fetch(`${getBaseUrl()}/api/auth/me`);
      if (res.ok) {
        const data = await res.json();
        if (data && data.name) {
          setUser({ name: data.name, email: data.email });
        }
      }
    } catch (err) {
      console.error(err);
    }
  }

  function handleOpenModal() {
    setNameInput(user.name);
    setEmailInput(user.email);
    setShowModal(true);
  }

  async function handleSaveProfile(e: React.FormEvent) {
    e.preventDefault();
    if (!nameInput.trim() || !emailInput.trim()) return;

    setSaving(true);
    try {
      const res = await fetch(`${getBaseUrl()}/api/auth/profile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: nameInput.trim(),
          email: emailInput.trim(),
        }),
      });

      if (res.ok) {
        setUser({ name: nameInput.trim(), email: emailInput.trim() });
        setShowModal(false);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  }

  const initialLetter = user.name ? user.name.charAt(0).toUpperCase() : 'U';

  return (
    <>
      <aside className="w-56 flex-shrink-0 flex flex-col bg-[#1a1d27] border-r border-slate-800 h-screen">
        {/* Logo */}
        <div className="px-5 py-5 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white font-bold text-sm">
              P
            </div>
            <div>
              <p className="text-white font-bold text-sm leading-none">Personal AI</p>
              <p className="text-slate-500 text-[10px] mt-0.5">Assistant Agent</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {NAV_ITEMS.map(({ href, icon, label }) => {
            const active = pathname === href || (href !== '/' && pathname.startsWith(href));
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  active
                    ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                }`}
              >
                <span className="text-base">{icon}</span>
                {label}
              </Link>
            );
          })}
        </nav>

        {/* Footer — user info with edit button */}
        <div className="px-3 py-3 border-t border-slate-800">
          <div
            onClick={handleOpenModal}
            className="flex items-center justify-between p-2 rounded-xl hover:bg-slate-800/80 cursor-pointer transition-all group border border-transparent hover:border-slate-700"
            title="Click to set your own name and email"
          >
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center text-xs text-white font-bold flex-shrink-0 shadow-md">
                {initialLetter}
              </div>
              <div className="overflow-hidden">
                <p className="text-white text-xs font-semibold truncate group-hover:text-indigo-300 transition-colors">
                  {user.name}
                </p>
                <p className="text-slate-400 text-[10px] truncate">{user.email}</p>
              </div>
            </div>
            <span className="text-slate-500 group-hover:text-slate-300 text-xs px-1">✏️</span>
          </div>
        </div>
      </aside>

      {/* Edit Profile Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in">
          <div className="bg-[#1a1d27] border border-slate-700 rounded-2xl p-6 max-w-sm w-full shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-white font-bold text-sm flex items-center gap-2">
                <span>👤</span> Set Your Account Profile
              </h3>
              <button
                onClick={() => setShowModal(false)}
                className="text-slate-400 hover:text-white text-sm cursor-pointer"
              >
                ✕
              </button>
            </div>

            <p className="text-slate-400 text-xs">
              Personalize Personal AI Assistant with your own name and email address:
            </p>

            <form onSubmit={handleSaveProfile} className="space-y-3">
              <div>
                <label className="block text-[11px] font-medium text-slate-300 mb-1">
                  Your Full Name
                </label>
                <input
                  type="text"
                  value={nameInput}
                  onChange={(e) => setNameInput(e.target.value)}
                  placeholder="e.g. Karan Patil"
                  className="w-full bg-[#12141c] border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  required
                />
              </div>

              <div>
                <label className="block text-[11px] font-medium text-slate-300 mb-1">
                  Your Email Address
                </label>
                <input
                  type="email"
                  value={emailInput}
                  onChange={(e) => setEmailInput(e.target.value)}
                  placeholder="e.g. karanpatil3511@gmail.com"
                  className="w-full bg-[#12141c] border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  required
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-3 py-1.5 text-xs text-slate-400 hover:text-white cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold cursor-pointer shadow-md transition-all"
                >
                  {saving ? 'Saving...' : 'Save Profile'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
