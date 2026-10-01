import { useEffect, useRef } from 'react';
import { useChat } from '../hooks/useChat';
import { MessageBubble } from './MessageBubble';
import { InputBar } from './InputBar';
import type { ChatSettings } from '../types/settings';

interface ChatContainerProps {
  settings: ChatSettings;
}

export function ChatContainer({ settings }: ChatContainerProps) {
  const { messages, isLoading, error, sendMessage, clearMessages, sessionId } = useChat(settings);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="chat-interface">
      {/* Header */}
      <header className="chat-header">
        <div className="chat-header-left">
          <div className="chat-header-logo">
            <span>💬</span>
          </div>
          <div>
            <h1>SkilLab AI Chat</h1>
            <p>
              {sessionId ? `Session: ${sessionId.slice(0, 8)}...` : 'Multi-agent assistant'}
            </p>
          </div>
        </div>
        <button onClick={clearMessages} className="clear-button">
          <span>🗑️</span>
          Șterge
        </button>
      </header>

      {/* Messages area */}
      <main className="message-list">
        {messages.length === 0 ? (
          <div className="empty-state">
            <div className="icon">💬</div>
            <h3>Cum te pot ajuta?</h3>
            <p>
              Pot răspunde la întrebări despre licitații publice, achiziții directe,
              și pot analiza date din baza de date.
            </p>
            <div className="suggestions">
              <button
                onClick={() => sendMessage('Ce este o licitație deschisă?')}
                className="suggestion-btn"
              >
                Ce este o licitație deschisă?
              </button>
              <button
                onClick={() => sendMessage('Câte achiziții directe au fost în 2024?')}
                className="suggestion-btn"
              >
                Câte achiziții directe au fost în 2024?
              </button>
            </div>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            {isLoading && (
              <div className="thinking-indicator">
                <div className="thinking-dots">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
                Se procesează...
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </main>

      {/* Error display */}
      {error && (
        <div className="error-banner">{error}</div>
      )}

      {/* Input bar */}
      <InputBar onSend={sendMessage} isLoading={isLoading} />
    </div>
  );
}
