import type { IntentType } from '../../types/settings';

interface SettingsSectionProps {
  useGuardrails: boolean;
  memoryEnabled: boolean;
  persistMemory: boolean;
  cacheEnabled: boolean;
  intent: IntentType;
  onGuardrailsChange: (value: boolean) => void;
  onMemoryEnabledChange: (value: boolean) => void;
  onPersistMemoryChange: (value: boolean) => void;
  onCacheEnabledChange: (value: boolean) => void;
  onIntentChange: (value: IntentType) => void;
}

export function SettingsSection({
  useGuardrails,
  memoryEnabled,
  persistMemory,
  cacheEnabled,
  intent,
  onGuardrailsChange,
  onMemoryEnabledChange,
  onPersistMemoryChange,
  onCacheEnabledChange,
  onIntentChange,
}: SettingsSectionProps) {
  return (
    <div className="sidebar-section">
      <h3 className="sidebar-section-title">
        <span className="icon">&#x2699;</span>
        Features
      </h3>

      <div className="setting-group">
        <label className="setting-label">Intent</label>
        <select
          className="setting-select"
          value={intent}
          onChange={(e) => onIntentChange(e.target.value as IntentType)}
        >
          <option value="auto">Auto-detect</option>
          <option value="chat">Chat (Direct LLM)</option>
          <option value="rag">RAG (Documents)</option>
          <option value="sql">SQL (Database)</option>
        </select>
      </div>

      <div className="setting-toggle-group">
        <label className="setting-toggle">
          <input
            type="checkbox"
            checked={useGuardrails}
            onChange={(e) => onGuardrailsChange(e.target.checked)}
          />
          <span className="toggle-slider"></span>
          <span className="toggle-label">
            Guardrails
            <span className="toggle-description">Input validation</span>
          </span>
        </label>

        <label className="setting-toggle">
          <input
            type="checkbox"
            checked={memoryEnabled}
            onChange={(e) => onMemoryEnabledChange(e.target.checked)}
          />
          <span className="toggle-slider"></span>
          <span className="toggle-label">
            Memory
            <span className="toggle-description">In-session context</span>
          </span>
        </label>

        <label className="setting-toggle">
          <input
            type="checkbox"
            checked={persistMemory}
            disabled={!memoryEnabled}
            onChange={(e) => onPersistMemoryChange(e.target.checked)}
          />
          <span className="toggle-slider"></span>
          <span className="toggle-label">
            Persist to DB
            <span className="toggle-description">Cross-session memory</span>
          </span>
        </label>

        <label className="setting-toggle">
          <input
            type="checkbox"
            checked={cacheEnabled}
            onChange={(e) => onCacheEnabledChange(e.target.checked)}
          />
          <span className="toggle-slider"></span>
          <span className="toggle-label">
            Cache
            <span className="toggle-description">Semantic caching</span>
          </span>
        </label>
      </div>
    </div>
  );
}
