export interface LLMMetrics {
  provider: string | null;
  model: string | null;
  input_tokens: number;
  output_tokens: number;
  cache_read_tokens: number;
  latency_ms: number;
  calls_count: number;
}

export interface GuardrailsMetrics {
  checked: boolean;
  safe: boolean;
  blocked_category: string | null;
}

export interface CacheMetrics {
  semantic_hit: boolean;
  prompt_cache_hit: boolean;
}

export interface MemoryMetrics {
  messages_count: number;
  session_id: string | null;
}

export interface AgentMetrics {
  type: string | null;
  iterations: number;
  sql_query: string | null;
  retry_count: number;
  steps_count: number;
}

export interface ChatMetrics {
  llm: LLMMetrics;
  guardrails: GuardrailsMetrics;
  cache: CacheMetrics;
  memory: MemoryMetrics;
  agent: AgentMetrics;
}

import type { ChatSettings } from './settings';

export interface ChatRequest {
  message: string;
  session_id?: string;
  intent?: 'rag' | 'sql' | 'chat';
  settings?: ChatSettings;
}

export interface ChatResponse {
  answer: string;
  session_id: string | null;
  intent: 'rag' | 'sql' | 'chat';
  status: 'success' | 'partial' | 'failed' | 'blocked';
  metrics: ChatMetrics;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  metrics?: ChatMetrics;
  intent?: 'rag' | 'sql' | 'chat';
  status?: string;
}
