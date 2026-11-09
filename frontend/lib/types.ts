// types.ts — TypeScript type definitions matching backend Pydantic schemas
// Keep in sync with backend/app/schemas/

export interface TraceStep {
  status: 'ok' | 'warning' | 'error' | 'pending';
  message: string;
  detail?: string;
}

export interface ActionStep {
  order: number;
  service: 'gmail' | 'calendar' | 'drive' | 'system';
  action: string;
  description?: string;
  requires_approval: boolean;
  status: 'pending' | 'running' | 'done' | 'failed' | 'awaiting_approval';
}

export interface ActionPlan {
  goal: string;
  steps: ActionStep[];
}

export interface ChatRequest {
  message: string;
  conversation_id?: number;
}

export interface ChatResponse {
  conversation_id: number;
  message_id: number;
  reply: string;
  action_plan_id?: number;
  action_plan?: ActionPlan;
  trace: TraceStep[];
  requires_approval: boolean;
  approval_action?: Record<string, unknown>;
  integration_status?: 'connected' | 'fallback' | 'demo';
  model_name?: string;
  is_fallback?: boolean;
  error_detail?: string;
}

export interface Message {
  id: number;
  role: 'user' | 'model' | 'system' | 'tool';
  content: string;
  created_at: string;
  // Frontend-only fields attached after receiving ChatResponse
  action_plan_id?: number;
  action_plan?: ActionPlan;
  trace?: TraceStep[];
  requires_approval?: boolean;
  approval_action?: Record<string, unknown>;
  integration_status?: 'connected' | 'fallback' | 'demo';
  model_name?: string;
  is_fallback?: boolean;
  error_detail?: string;
}

export interface Memory {
  id: number;
  key: string;
  value: string;
  category: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface AuditLog {
  id: number;
  action_type: string;
  service: string;
  tool_name: string;
  input_summary?: string;
  result_summary?: string;
  status: string;
  approval_required: boolean;
  approval_status?: string;
  created_at: string;
}

export interface Conversation {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface UserProfile {
  id: number;
  name: string;
  email: string;
  profile_picture?: string;
  auth_mode?: string;
  google_connected?: boolean;
  simulated_connected?: boolean;
  services?: Record<string, boolean>;
  mode?: string;
}

export interface HealthStatus {
  status: string;
  service: string;
  version: string;
  gemini_configured: boolean;
  google_oauth_configured: boolean;
}
