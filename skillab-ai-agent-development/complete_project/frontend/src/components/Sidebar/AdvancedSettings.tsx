import { useState } from 'react';

interface AdvancedSettingsProps {
  ragTopK: number;
  ragThreshold: number;
  maxIterations: number;
  maxRetries: number;
  useLlmInjection: boolean;
  cacheTtlHours: number;
  onRagTopKChange: (value: number) => void;
  onRagThresholdChange: (value: number) => void;
  onMaxIterationsChange: (value: number) => void;
  onMaxRetriesChange: (value: number) => void;
  onUseLlmInjectionChange: (value: boolean) => void;
  onCacheTtlHoursChange: (value: number) => void;
}

export function AdvancedSettings({
  ragTopK,
  ragThreshold,
  maxIterations,
  maxRetries,
  useLlmInjection,
  cacheTtlHours,
  onRagTopKChange,
  onRagThresholdChange,
  onMaxIterationsChange,
  onMaxRetriesChange,
  onUseLlmInjectionChange,
  onCacheTtlHoursChange,
}: AdvancedSettingsProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="sidebar-section advanced-section">
      <button
        className="advanced-toggle"
        onClick={() => setIsOpen(!isOpen)}
        type="button"
      >
        <span className="icon">&#x1F527;</span>
        Advanced Settings
        <span className={`chevron ${isOpen ? 'open' : ''}`}>&#x25BC;</span>
      </button>

      {isOpen && (
        <div className="advanced-content">
          {/* RAG Settings */}
          <div className="advanced-group">
            <h4 className="advanced-group-title">RAG</h4>

            <div className="setting-group">
              <label className="setting-label">
                Top K
                <span className="setting-value">{ragTopK}</span>
              </label>
              <input
                type="range"
                className="setting-slider"
                min="1"
                max="20"
                step="1"
                value={ragTopK}
                onChange={(e) => onRagTopKChange(parseInt(e.target.value))}
              />
            </div>

            <div className="setting-group">
              <label className="setting-label">
                Threshold
                <span className="setting-value">{ragThreshold.toFixed(2)}</span>
              </label>
              <input
                type="range"
                className="setting-slider"
                min="0"
                max="1"
                step="0.05"
                value={ragThreshold}
                onChange={(e) => onRagThresholdChange(parseFloat(e.target.value))}
              />
            </div>
          </div>

          {/* Agent Settings */}
          <div className="advanced-group">
            <h4 className="advanced-group-title">Agent</h4>

            <div className="setting-group">
              <label className="setting-label">
                Max Iterations
                <span className="setting-value">{maxIterations}</span>
              </label>
              <input
                type="range"
                className="setting-slider"
                min="1"
                max="10"
                step="1"
                value={maxIterations}
                onChange={(e) => onMaxIterationsChange(parseInt(e.target.value))}
              />
            </div>

            <div className="setting-group">
              <label className="setting-label">
                Max Retries
                <span className="setting-value">{maxRetries}</span>
              </label>
              <input
                type="range"
                className="setting-slider"
                min="0"
                max="5"
                step="1"
                value={maxRetries}
                onChange={(e) => onMaxRetriesChange(parseInt(e.target.value))}
              />
            </div>
          </div>

          {/* Security Settings */}
          <div className="advanced-group">
            <h4 className="advanced-group-title">Security</h4>

            <label className="setting-toggle">
              <input
                type="checkbox"
                checked={useLlmInjection}
                onChange={(e) => onUseLlmInjectionChange(e.target.checked)}
              />
              <span className="toggle-slider"></span>
              <span className="toggle-label">
                LLM Injection Check
                <span className="toggle-description">Extra security layer</span>
              </span>
            </label>
          </div>

          {/* Cache Settings */}
          <div className="advanced-group">
            <h4 className="advanced-group-title">Cache</h4>

            <div className="setting-group">
              <label className="setting-label">
                TTL (hours)
                <span className="setting-value">{cacheTtlHours}</span>
              </label>
              <input
                type="range"
                className="setting-slider"
                min="1"
                max="24"
                step="1"
                value={cacheTtlHours}
                onChange={(e) => onCacheTtlHoursChange(parseInt(e.target.value))}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
