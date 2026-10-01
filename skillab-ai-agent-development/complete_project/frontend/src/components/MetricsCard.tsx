import { useState } from 'react';
import type { ChatMetrics } from '../types/api';

interface MetricsCardProps {
  metrics: ChatMetrics;
  intent: 'rag' | 'sql' | 'chat';
  status: string;
}

function Badge({ children, variant = 'default' }: { children: React.ReactNode; variant?: string }) {
  return <span className={`badge ${variant}`}>{children}</span>;
}

function MetricRow({ label, value, isCode = false }: { label: string; value: string | number | null; isCode?: boolean }) {
  if (value === null || value === undefined) return null;
  return (
    <div className="metrics-row">
      <span className="label">{label}</span>
      <span className={`value ${isCode ? 'code' : ''}`}>{value}</span>
    </div>
  );
}

export function MetricsCard({ metrics, intent, status }: MetricsCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const statusVariant = {
    success: 'success',
    partial: 'warning',
    failed: 'error',
    blocked: 'error',
  }[status] || 'default';

  const totalTokens = metrics.llm.input_tokens + metrics.llm.output_tokens;
  const cacheReadTokens = metrics.llm.cache_read_tokens || 0;

  return (
    <div className="metrics-card">
      {/* Header - always visible */}
      <div className="metrics-header" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="metrics-badges">
          <Badge variant={statusVariant}>{status}</Badge>
          <Badge variant="info">{intent.toUpperCase()}</Badge>
          {metrics.llm.provider && (
            <Badge variant="accent">{metrics.llm.provider}</Badge>
          )}
          {cacheReadTokens > 0 && (
            <Badge variant="success">cached</Badge>
          )}
        </div>
        <div className="metrics-summary">
          <span>{totalTokens} tokens</span>
          {cacheReadTokens > 0 && (
            <span className="cache-indicator">⚡ {cacheReadTokens} cached</span>
          )}
          <span>{metrics.llm.latency_ms}ms</span>
          <span className={`chevron ${isExpanded ? 'open' : ''}`}>▼</span>
        </div>
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div className="metrics-content">
          {/* LLM Metrics */}
          <div className="metrics-section">
            <div className="metrics-section-header">
              <span className="icon">🤖</span>
              LLM Usage
            </div>
            <MetricRow label="Provider" value={metrics.llm.provider} />
            <MetricRow label="Model" value={metrics.llm.model} />
            <MetricRow label="Input Tokens" value={metrics.llm.input_tokens} />
            <MetricRow label="Output Tokens" value={metrics.llm.output_tokens} />
            <MetricRow label="Cache Read" value={metrics.llm.cache_read_tokens} />
            <MetricRow label="Latency" value={`${metrics.llm.latency_ms}ms`} />
            <MetricRow label="API Calls" value={metrics.llm.calls_count} />
          </div>

          {/* Guardrails */}
          <div className="metrics-section">
            <div className="metrics-section-header">
              <span className="icon">🛡️</span>
              Guardrails
            </div>
            <div className="metrics-row">
              <span className="label">Checked</span>
              <Badge variant={metrics.guardrails.checked ? 'success' : 'default'}>
                {metrics.guardrails.checked ? 'Yes' : 'No'}
              </Badge>
            </div>
            <div className="metrics-row">
              <span className="label">Safe</span>
              <Badge variant={metrics.guardrails.safe ? 'success' : 'error'}>
                {metrics.guardrails.safe ? 'Yes' : 'No'}
              </Badge>
            </div>
            {metrics.guardrails.blocked_category && (
              <MetricRow label="Blocked" value={metrics.guardrails.blocked_category} />
            )}
          </div>

          {/* Agent Info */}
          <div className="metrics-section">
            <div className="metrics-section-header">
              <span className="icon">⚙️</span>
              Agent
            </div>
            <MetricRow label="Type" value={metrics.agent.type} />
            <MetricRow label="Iterations" value={metrics.agent.iterations} />
            <MetricRow label="Steps" value={metrics.agent.steps_count} />
            <MetricRow label="Retries" value={metrics.agent.retry_count} />
            {metrics.agent.sql_query && (
              <div className="sql-display">
                <div className="label">SQL Query:</div>
                <pre>{metrics.agent.sql_query}</pre>
              </div>
            )}
          </div>

          {/* Memory */}
          <div className="metrics-section">
            <div className="metrics-section-header">
              <span className="icon">💬</span>
              Memory
            </div>
            <MetricRow label="Messages" value={metrics.memory.messages_count} />
            {metrics.memory.session_id && (
              <MetricRow label="Session" value={metrics.memory.session_id.slice(0, 8) + '...'} isCode />
            )}
          </div>

          {/* Cache */}
          <div className="metrics-section">
            <div className="metrics-section-header">
              <span className="icon">📦</span>
              Cache
            </div>
            <div className="metrics-row">
              <span className="label">Semantic Hit</span>
              <Badge variant={metrics.cache.semantic_hit ? 'success' : 'default'}>
                {metrics.cache.semantic_hit ? 'Yes' : 'No'}
              </Badge>
            </div>
            <div className="metrics-row">
              <span className="label">Prompt Cache</span>
              <Badge variant={metrics.cache.prompt_cache_hit ? 'success' : 'default'}>
                {metrics.cache.prompt_cache_hit ? 'Yes' : 'No'}
              </Badge>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
