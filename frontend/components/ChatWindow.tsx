'use client';

// ChatWindow.tsx — Main chat interface component
// Handles sending messages, displaying history, and showing agent responses

import { useState, useRef, useEffect } from 'react';
import { api } from '@/lib/api';
import type { Message } from '@/lib/types';
import { MessageBubble } from './MessageBubble';

const SUGGESTED_PROMPTS = [
  "Find tomorrow's project meeting and prepare an email for participants",
  "What meetings do I have today?",
  "Search my Drive for the latest project report",
  "Find emails about assignment deadlines this week",
];

export function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fastMode, setFastMode] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Check for pre-selected workflow launch from Workflows page
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const initialPrompt = sessionStorage.getItem('assistant_initial_prompt');
      if (initialPrompt) {
        sessionStorage.removeItem('assistant_initial_prompt');
        sendMessage(initialPrompt);
      }
    }
  }, []);

  async function sendMessage(text?: string) {
    const messageText = (text ?? input).trim();
    if (!messageText || loading) return;

    setInput('');
    setError(null);

    // Optimistically add user message
    const userMsg: Message = {
      id: Date.now(),
      role: 'user',
      content: messageText,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const response = await api.sendMessage({
        message: messageText,
        conversation_id: conversationId ?? undefined,
      });

      // Save the conversation ID for subsequent messages
      if (!conversationId) setConversationId(response.conversation_id);

      // Add assistant reply with trace and plan attached
      const assistantMsg: Message = {
        id: response.message_id,
        role: 'model',
        content: response.reply,
        created_at: new Date().toISOString(),
        action_plan_id: response.action_plan_id,
        action_plan: response.action_plan ?? undefined,
        trace: response.trace,
        requires_approval: response.requires_approval,
        approval_action: response.approval_action ?? undefined,
        integration_status: response.integration_status,
        model_name: response.model_name,
        is_fallback: response.is_fallback,
        error_detail: response.error_detail,
      };
      setMessages((prev) => [...prev, assistantMsg]);

      // If Fast Mode is ON, immediately approve and execute without waiting
      if (fastMode && response.requires_approval && response.action_plan_id) {
        api.handleApproval({ action_plan_id: response.action_plan_id, approved: true })
          .then(() => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsg.id
                  ? {
                      ...m,
                      requires_approval: false,
                      content: m.content + '\n\n⚡ *Auto-approved and executed in Fast Mode.*',
                    }
                  : m
              )
            );
          })
          .catch((err) => {
            const errMsg = err instanceof Error ? err.message : 'Fast mode approval failed';
            setError(`Approval failed: ${errMsg}`);
            console.error('Fast mode approval error:', err);
          });
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setError(msg);
      // Remove optimistic user message on failure
      setMessages((prev) => prev.filter((m) => m.id !== userMsg.id));
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Top bar */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-[#1a1d27]">
        <div>
          <h1 className="text-white font-semibold">💬 Chat</h1>
          <p className="text-slate-500 text-xs">
            {conversationId ? `Conversation #${conversationId}` : 'New conversation'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setFastMode((prev) => !prev)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer transition-all flex items-center gap-1.5 border ${
              fastMode
                ? 'bg-amber-500/20 text-amber-300 border-amber-500/50 shadow-sm shadow-amber-500/20'
                : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-white'
            }`}
            title="When Fast Mode is ON, sensitive actions are auto-approved instantly without pausing"
          >
            <span>⚡ Fast Mode:</span>
            <span className={fastMode ? 'text-amber-400 font-bold' : 'text-slate-500'}>
              {fastMode ? 'ON (Auto-Approve)' : 'OFF'}
            </span>
          </button>

          {conversationId && (
            <button
              onClick={() => { setMessages([]); setConversationId(null); }}
              className="text-xs text-slate-500 hover:text-white px-3 py-1.5 rounded-lg hover:bg-slate-700"
            >
              + New Chat
            </button>
          )}
        </div>
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center py-12">
            <div className="text-5xl mb-4">🤖</div>
            <h2 className="text-xl font-semibold text-white mb-2">Personal AI Assistant is ready</h2>
            <p className="text-slate-400 text-sm max-w-sm mb-8">
              Ask me anything about your Gmail, Calendar, or Drive — or try one of these:
            </p>
            <div className="grid grid-cols-1 gap-2 w-full max-w-lg">
              {SUGGESTED_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => sendMessage(prompt)}
                  className="text-left px-4 py-3 rounded-xl border border-slate-700 hover:border-indigo-500/50 hover:bg-indigo-500/5 text-slate-300 text-sm transition-all"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {/* Loading indicator */}
        {loading && (
          <div className="flex items-start gap-2">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider mt-1">🤖 ORBIT 180</span>
            <div className="bg-[#1e2130] border border-slate-700 rounded-2xl rounded-tl-none px-4 py-3">
              <div className="flex gap-1.5 items-center">
                <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce [animation-delay:0ms]" />
                <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce [animation-delay:150ms]" />
                <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}

        {/* Error banner */}
        {error && (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-red-400 text-sm">
            ⚠ {error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="px-6 py-4 border-t border-slate-800 bg-[#1a1d27]">
        <div className="flex gap-3 items-end rounded-2xl border border-slate-700 focus-within:border-indigo-500/60 bg-[#141720] px-4 py-3">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask ORBIT 180... (Enter to send, Shift+Enter for new line)"
            rows={1}
            className="flex-1 bg-transparent text-slate-200 placeholder-slate-600 text-sm resize-none outline-none leading-relaxed max-h-32 overflow-y-auto"
            style={{ height: 'auto' }}
            onInput={(e) => {
              const el = e.currentTarget;
              el.style.height = 'auto';
              el.style.height = `${el.scrollHeight}px`;
            }}
          />
          <button
            onClick={() => sendMessage()}
            disabled={!input.trim() || loading}
            className="flex-shrink-0 w-8 h-8 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center text-white text-sm transition-all"
          >
            ↑
          </button>
        </div>
        <p className="text-[10px] text-slate-600 mt-2 text-center">
          ORBIT 180 can make mistakes. Review sensitive actions before approving.
        </p>
      </div>
    </div>
  );
}
