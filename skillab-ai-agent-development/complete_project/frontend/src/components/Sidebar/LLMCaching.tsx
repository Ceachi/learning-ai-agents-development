import { useState } from 'react';

interface LLMCachingProps {
  enabled: boolean;
  context: string;
  onEnabledChange: (enabled: boolean) => void;
  onContextChange: (context: string) => void;
}

export function LLMCaching({
  enabled,
  context,
  onEnabledChange,
  onContextChange,
}: LLMCachingProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Estimate token count (~4 chars per token for Romanian text)
  const estimatedTokens = Math.round(context.length / 4);

  return (
    <div className="sidebar-section llm-caching-section">
      <div className="llm-caching-header">
        <label className="setting-toggle">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => onEnabledChange(e.target.checked)}
          />
          <span className="toggle-slider"></span>
          <span className="toggle-label">
            <span className="llm-caching-title">
              <span className="icon">&#x1F9E0;</span>
              LLM Caching
            </span>
            <span className="toggle-description">
              Cache system context for faster responses
            </span>
          </span>
        </label>
      </div>

      {enabled && (
        <div className="llm-caching-content">
          <button
            className="context-toggle"
            onClick={() => setIsExpanded(!isExpanded)}
            type="button"
          >
            <span>System Context</span>
            <span className="token-badge">~{estimatedTokens.toLocaleString()} tokens</span>
            <span className={`chevron ${isExpanded ? 'open' : ''}`}>&#x25BC;</span>
          </button>

          {isExpanded && (
            <textarea
              className="context-textarea"
              value={context}
              onChange={(e) => onContextChange(e.target.value)}
              placeholder="Enter system context to be cached..."
              rows={8}
            />
          )}

          <div className="caching-info">
            <div className="info-item">
              <span className="info-icon">&#x26A1;</span>
              <span>First request creates cache</span>
            </div>
            <div className="info-item">
              <span className="info-icon">&#x1F4B0;</span>
              <span>Subsequent requests use cached tokens</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
