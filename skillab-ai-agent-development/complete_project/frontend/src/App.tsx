import { ChatContainer } from './components/ChatContainer';
import { Sidebar } from './components/Sidebar';
import { useSettings } from './hooks/useSettings';

function App() {
  const {
    settings,
    providers,
    availableModels,
    defaultModel,
    updateSetting,
    resetSettings,
  } = useSettings();

  return (
    <div className="app-layout">
      <Sidebar
        settings={settings}
        providers={providers}
        availableModels={availableModels}
        defaultModel={defaultModel}
        onUpdateSetting={updateSetting}
        onResetSettings={resetSettings}
      />
      <main className="main-content">
        <ChatContainer settings={settings} />
      </main>
    </div>
  );
}

export default App;
