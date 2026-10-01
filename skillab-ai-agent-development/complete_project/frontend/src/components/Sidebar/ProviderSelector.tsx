import type { LLMProvider, ProviderConfig } from '../../types/settings';

interface ProviderSelectorProps {
  provider: LLMProvider;
  model: string | null;
  temperature: number;
  providers: ProviderConfig[];
  availableModels: string[];
  defaultModel: string | null;
  onProviderChange: (provider: LLMProvider) => void;
  onModelChange: (model: string | null) => void;
  onTemperatureChange: (temp: number) => void;
}

export function ProviderSelector({
  provider,
  model,
  temperature,
  providers,
  availableModels,
  defaultModel,
  onProviderChange,
  onModelChange,
  onTemperatureChange,
}: ProviderSelectorProps) {
  const handleProviderChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newProvider = e.target.value as LLMProvider;
    onProviderChange(newProvider);
    // Reset model when provider changes
    onModelChange(null);
  };

  const handleModelChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    onModelChange(value === '' ? null : value);
  };

  const handleTempChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onTemperatureChange(parseFloat(e.target.value));
  };

  const displayModel = model || defaultModel || '';

  return (
    <div className="sidebar-section">
      <h3 className="sidebar-section-title">
        <span className="icon">&#x1F916;</span>
        LLM Configuration
      </h3>

      <div className="setting-group">
        <label className="setting-label">Provider</label>
        <select
          className="setting-select"
          value={provider}
          onChange={handleProviderChange}
        >
          {providers.map((p) => (
            <option key={p.name} value={p.name}>
              {p.name.charAt(0).toUpperCase() + p.name.slice(1)}
            </option>
          ))}
        </select>
      </div>

      <div className="setting-group">
        <label className="setting-label">Model</label>
        <select
          className="setting-select"
          value={displayModel}
          onChange={handleModelChange}
        >
          {availableModels.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </div>

      <div className="setting-group">
        <label className="setting-label">
          Temperature
          <span className="setting-value">{temperature.toFixed(1)}</span>
        </label>
        <input
          type="range"
          className="setting-slider"
          min="0"
          max="1"
          step="0.1"
          value={temperature}
          onChange={handleTempChange}
        />
        <div className="slider-labels">
          <span>Precise</span>
          <span>Creative</span>
        </div>
      </div>
    </div>
  );
}
