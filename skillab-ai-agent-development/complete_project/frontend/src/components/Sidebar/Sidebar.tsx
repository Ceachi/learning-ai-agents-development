import type { ChatSettings, ProviderConfig, LLMProvider, IntentType } from '../../types/settings';
import { ProviderSelector } from './ProviderSelector';
import { SettingsSection } from './SettingsSection';
import { AdvancedSettings } from './AdvancedSettings';
import { LLMCaching } from './LLMCaching';

interface SidebarProps {
  settings: ChatSettings;
  providers: ProviderConfig[];
  availableModels: string[];
  defaultModel: string | null;
  onUpdateSetting: <K extends keyof ChatSettings>(key: K, value: ChatSettings[K]) => void;
  onResetSettings: () => void;
}

export function Sidebar({
  settings,
  providers,
  availableModels,
  defaultModel,
  onUpdateSetting,
  onResetSettings,
}: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <span className="logo-icon">S</span>
        </div>
        <div className="sidebar-title">
          <h2>SkilLab AI</h2>
          <p>Configuration</p>
        </div>
      </div>

      <div className="sidebar-content">
        <ProviderSelector
          provider={settings.llm_provider}
          model={settings.llm_model}
          temperature={settings.llm_temperature}
          providers={providers}
          availableModels={availableModels}
          defaultModel={defaultModel}
          onProviderChange={(p: LLMProvider) => onUpdateSetting('llm_provider', p)}
          onModelChange={(m: string | null) => onUpdateSetting('llm_model', m)}
          onTemperatureChange={(t: number) => onUpdateSetting('llm_temperature', t)}
        />

        <SettingsSection
          useGuardrails={settings.use_guardrails}
          memoryEnabled={settings.memory_enabled}
          persistMemory={settings.persist_memory}
          cacheEnabled={settings.cache_enabled}
          intent={settings.intent}
          onGuardrailsChange={(v: boolean) => onUpdateSetting('use_guardrails', v)}
          onMemoryEnabledChange={(v: boolean) => onUpdateSetting('memory_enabled', v)}
          onPersistMemoryChange={(v: boolean) => onUpdateSetting('persist_memory', v)}
          onCacheEnabledChange={(v: boolean) => onUpdateSetting('cache_enabled', v)}
          onIntentChange={(v: IntentType) => onUpdateSetting('intent', v)}
        />

        <LLMCaching
          enabled={settings.llm_caching_enabled}
          context={settings.llm_caching_context}
          onEnabledChange={(v: boolean) => onUpdateSetting('llm_caching_enabled', v)}
          onContextChange={(v: string) => onUpdateSetting('llm_caching_context', v)}
        />

        <AdvancedSettings
          ragTopK={settings.rag_top_k}
          ragThreshold={settings.rag_threshold}
          maxIterations={settings.max_iterations}
          maxRetries={settings.max_retries}
          useLlmInjection={settings.use_llm_injection}
          cacheTtlHours={settings.cache_ttl_hours}
          onRagTopKChange={(v: number) => onUpdateSetting('rag_top_k', v)}
          onRagThresholdChange={(v: number) => onUpdateSetting('rag_threshold', v)}
          onMaxIterationsChange={(v: number) => onUpdateSetting('max_iterations', v)}
          onMaxRetriesChange={(v: number) => onUpdateSetting('max_retries', v)}
          onUseLlmInjectionChange={(v: boolean) => onUpdateSetting('use_llm_injection', v)}
          onCacheTtlHoursChange={(v: number) => onUpdateSetting('cache_ttl_hours', v)}
        />
      </div>

      <div className="sidebar-footer">
        <button
          className="reset-button"
          onClick={onResetSettings}
          type="button"
        >
          Reset to Defaults
        </button>
      </div>
    </aside>
  );
}
