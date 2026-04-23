import { supabase } from './supabaseClient';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface ChatResponse {
  answer: string;
  source: { source: string; page: string }[];
  usage_remaining: number | string;
  llm_used?: string;
}

export interface Module {
  id: string;
  name: string;
  streams: string[];
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const { data } = await supabase.auth.getSession();
  const token = data?.session?.access_token;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'ngrok-skip-browser-warning': 'true',
    ...((options.headers as Record<string, string>) || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    headers,
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function askQuestion(
  question: string,
  module: string,
  userId?: string,
  preferredLlm?: string,
  history?: { role: string; content: string }[]
): Promise<ChatResponse> {
  return request<ChatResponse>('/chat', {
    method: 'POST',
    body: JSON.stringify({
      question,
      module,
      user_id: userId,
      preferred_llm: preferredLlm,
      history: history || [],
    }),
  });
}

export async function getModules(): Promise<{ modules: Module[] }> {
  return request<{ modules: Module[] }>('/modules');
}

export async function login(email: string, password: string) {
  return request<{ access_token: string; user: Record<string, unknown> }>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}
