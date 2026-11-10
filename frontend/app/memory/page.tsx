'use client';

// app/memory/page.tsx — User memory management page
// Users can view, add, toggle, and delete their saved preferences

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import type { Memory } from '@/lib/types';

const CATEGORIES = ['general', 'scheduling', 'communication', 'privacy', 'workflow'];

export default function MemoryPage() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [newKey, setNewKey] = useState('');
  const [newValue, setNewValue] = useState('');
  const [newCategory, setNewCategory] = useState('general');

  useEffect(() => {
    api.getMemories()
      .then(setMemories)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  async function handleAdd() {
    if (!newKey.trim() || !newValue.trim()) return;
    try {
      const mem = await api.createMemory({ key: newKey, value: newValue, category: newCategory });
      setMemories((prev) => [mem, ...prev]);
      setNewKey(''); setNewValue(''); setNewCategory('general'); setAdding(false);
    } catch (e) { console.error(e); }
  }

  async function handleToggle(mem: Memory) {
    try {
      const updated = await api.updateMemory(mem.id, { enabled: !mem.enabled });
      setMemories((prev) => prev.map((m) => (m.id === updated.id ? updated : m)));
    } catch (e) { console.error(e); }
  }

  async function handleDelete(id: number) {
    if (!confirm('Delete this memory?')) return;
    try {
      await api.deleteMemory(id);
      setMemories((prev) => prev.filter((m) => m.id !== id));
    } catch (e) { console.error(e); }
  }

  return (
    <div className="flex-1 overflow-y-auto p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">🧠 Memory</h1>
          <p className="text-slate-400 text-sm mt-1">
            Saved preferences that Personal AI Assistant uses when planning actions
          </p>
        </div>
        <button
          onClick={() => setAdding(true)}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-xl"
        >
          + Add Memory
        </button>
      </div>

      {/* Add form */}
      {adding && (
        <div className="mb-6 rounded-xl border border-indigo-500/30 bg-indigo-500/5 p-5">
          <h3 className="text-sm font-semibold text-white mb-4">New Memory</h3>
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Key (what to remember)</label>
              <input
                value={newKey}
                onChange={(e) => setNewKey(e.target.value)}
                placeholder="e.g. preferred_meeting_time"
                className="w-full bg-[#1a1d27] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Category</label>
              <select
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value)}
                className="w-full bg-[#1a1d27] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white outline-none"
              >
                {CATEGORIES.map((c) => <option key={c}>{c}</option>)}
              </select>
            </div>
          </div>
          <div className="mb-3">
            <label className="text-xs text-slate-400 mb-1 block">Value</label>
            <input
              value={newValue}
              onChange={(e) => setNewValue(e.target.value)}
              placeholder="e.g. 11 AM to 4 PM"
              className="w-full bg-[#1a1d27] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-indigo-500"
            />
          </div>
          <div className="flex gap-2">
            <button onClick={handleAdd} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm rounded-lg">Save</button>
            <button onClick={() => setAdding(false)} className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 text-sm rounded-lg">Cancel</button>
          </div>
        </div>
      )}

      {/* Seed memories hint */}
      {memories.length === 0 && !loading && (
        <div className="rounded-xl border border-slate-700 bg-[#1a1d27] p-8 text-center">
          <p className="text-slate-400 mb-2">No memories saved yet.</p>
          <p className="text-slate-500 text-sm">Add preferences like:</p>
          <div className="mt-3 space-y-1 text-slate-500 text-xs">
            <p>• preferred_meeting_time → 11 AM to 4 PM</p>
            <p>• avoid_weekend_meetings → true</p>
            <p>• preferred_language → English</p>
          </div>
        </div>
      )}

      {/* Memory list */}
      <div className="space-y-3">
        {memories.map((mem) => (
          <div
            key={mem.id}
            className={`rounded-xl border p-4 flex items-start gap-4 ${
              mem.enabled
                ? 'border-slate-700 bg-[#1a1d27]'
                : 'border-slate-800 bg-[#141720] opacity-60'
            }`}
          >
            {/* Toggle */}
            <button
              onClick={() => handleToggle(mem)}
              className={`mt-0.5 w-9 h-5 rounded-full flex-shrink-0 relative transition-all ${
                mem.enabled ? 'bg-indigo-600' : 'bg-slate-700'
              }`}
            >
              <span
                className={`absolute top-0.5 w-4 h-4 bg-white rounded-full transition-all ${
                  mem.enabled ? 'left-4' : 'left-0.5'
                }`}
              />
            </button>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-0.5">
                <span className="text-white text-sm font-medium">{mem.key}</span>
                <span className="text-[10px] text-slate-500 bg-slate-800 px-2 py-0.5 rounded-full">
                  {mem.category}
                </span>
              </div>
              <p className="text-slate-400 text-sm">{mem.value}</p>
            </div>

            {/* Delete */}
            <button
              onClick={() => handleDelete(mem.id)}
              className="text-slate-600 hover:text-red-400 text-sm flex-shrink-0"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
