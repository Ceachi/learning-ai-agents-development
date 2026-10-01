import { useState, useEffect, useCallback } from 'react';
import type { ChatSettings, ProviderConfig, ConfigResponse } from '../types/settings';
import { DEFAULT_SETTINGS } from '../types/settings';

const STORAGE_KEY = 'skillab-settings';
const API_BASE = '/api';

export function useSettings() {
  const [settings, setSettings] = useState<ChatSettings>(() => {
    // Load from localStorage on init
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        return { ...DEFAULT_SETTINGS, ...JSON.parse(stored) };
      }
    } catch (e) {
      console.error('Failed to load settings from localStorage:', e);
    }
    return DEFAULT_SETTINGS;
  });

  const [providers, setProviders] = useState<ProviderConfig[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch config from backend
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const response = await fetch(`${API_BASE}/config`);
        if (!response.ok) {
          throw new Error('Failed to fetch config');
        }
        const data: ConfigResponse = await response.json();
        setProviders(data.providers);
        setError(null);
      } catch (err) {
        console.error('Failed to fetch config:', err);
        setError('Failed to load configuration');
        // Use default providers on error
        setProviders([
          { name: 'ollama', models: ['llama3.2'], default_model: 'llama3.2' },
          { name: 'anthropic', models: ['claude-sonnet-4-20250514'], default_model: 'claude-sonnet-4-20250514' },
          { name: 'google', models: ['gemini-2.0-flash'], default_model: 'gemini-2.0-flash' },
        ]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchConfig();
  }, []);

  // Persist to localStorage on change
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    } catch (e) {
      console.error('Failed to save settings to localStorage:', e);
    }
  }, [settings]);

  const updateSetting = useCallback(<K extends keyof ChatSettings>(
    key: K,
    value: ChatSettings[K]
  ) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  }, []);

  const updateSettings = useCallback((updates: Partial<ChatSettings>) => {
    setSettings((prev) => ({ ...prev, ...updates }));
  }, []);

  const resetSettings = useCallback(() => {
    setSettings(DEFAULT_SETTINGS);
  }, []);

  // Get current provider config
  const currentProvider = providers.find((p) => p.name === settings.llm_provider);

  // Get models for current provider
  const availableModels = currentProvider?.models || [];

  // Get default model for current provider
  const defaultModel = currentProvider?.default_model || null;

  return {
    settings,
    providers,
    currentProvider,
    availableModels,
    defaultModel,
    isLoading,
    error,
    updateSetting,
    updateSettings,
    resetSettings,
  };
}
