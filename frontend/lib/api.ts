// api.ts — Typed API client for the Personal AI Assistant backend
// All fetch calls go through this file so base URLs are centralised.

import type {
  ChatRequest,
  ChatResponse,
  Memory,
  AuditLog,
  Conversation,
  UserProfile,
  HealthStatus,
} from './types';

export function getBaseUrl(): string {
  if (typeof window !== 'undefined' && window.location.hostname === '127.0.0.1') {
    return 'http://127.0.0.1:8000';
  }
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const baseUrl = getBaseUrl();
  const res = await fetch(`${baseUrl}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `Request failed: ${res.status}`);
  }

  // Handle 204 No Content
  if (res.status === 204) return undefined as unknown as T;

  return res.json() as Promise<T>;
}

export const api = {
  // Health
  health: () => apiFetch<HealthStatus>('/health'),

  // Auth
  getMe: () => apiFetch<UserProfile>('/api/auth/me'),
  getAuthStatus: () =>
    apiFetch<{ gemini_configured: boolean; google_oauth_configured: boolean; mock_mode: boolean }>(
      '/api/auth/status'
    ),

  // Chat
  sendMessage: (data: ChatRequest) =>
    apiFetch<ChatResponse>('/api/chat', { method: 'POST', body: JSON.stringify(data) }),
  getConversations: () => apiFetch<Conversation[]>('/api/chat/conversations'),
  getMessages: (conversationId: number) =>
    apiFetch<{ id: number; role: string; content: string; created_at: string }[]>(
      `/api/chat/conversations/${conversationId}/messages`
    ),

  // Memory
  getMemories: () => apiFetch<Memory[]>('/api/memory'),
  createMemory: (data: { key: string; value: string; category?: string }) =>
    apiFetch<Memory>('/api/memory', { method: 'POST', body: JSON.stringify(data) }),
  updateMemory: (id: number, data: Partial<Memory>) =>
    apiFetch<Memory>(`/api/memory/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteMemory: (id: number) => apiFetch<void>(`/api/memory/${id}`, { method: 'DELETE' }),

  // Audit
  getAuditLogs: (params?: { service?: string; status?: string; limit?: number }) => {
    const qs = new URLSearchParams();
    if (params?.service) qs.set('service', params.service);
    if (params?.status) qs.set('status', params.status);
    if (params?.limit) qs.set('limit', String(params.limit));
    return apiFetch<AuditLog[]>(`/api/audit?${qs.toString()}`);
  },

  // Approvals
  handleApproval: (data: { action_plan_id: number; approved: boolean; edited_action?: Record<string, unknown> }) =>
    apiFetch<{ status: string; approved: boolean; message: string }>('/api/approvals', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};
