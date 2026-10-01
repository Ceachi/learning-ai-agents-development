import type { Message } from '../types/api';
import { MetricsCard } from './MetricsCard';

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const hasContent = message.content.trim().length > 0;

  return (
    <div className={`message-bubble ${message.role}`}>
      {hasContent && <div className="message-content">{message.content}</div>}
      {!hasContent && message.role === 'assistant' && (
        <div className="message-content" style={{ opacity: 0.5 }}>
          ...
        </div>
      )}
      <div className="message-timestamp">
        {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
      </div>

      {/* Metrics card for assistant messages */}
      {message.role === 'assistant' && message.metrics && message.intent && message.status && (
        <MetricsCard
          metrics={message.metrics}
          intent={message.intent}
          status={message.status}
        />
      )}
    </div>
  );
}
