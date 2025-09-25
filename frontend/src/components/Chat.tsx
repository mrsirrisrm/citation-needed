import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2 } from 'lucide-react';
import { type ChatMessage, type Citation, type FactCheckResult, highlightCitations } from '../services/api';

interface ChatProps {
  messages: ChatMessage[];
  onSendMessage: (message: string) => Promise<void>;
  isLoading?: boolean;
  factCheckResults?: FactCheckResult[];
}

export const Chat: React.FC<ChatProps> = ({
  messages,
  onSendMessage,
  isLoading = false,
  factCheckResults = []
}) => {
  const [inputMessage, setInputMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (inputRef.current && !isSending && !isLoading) {
      inputRef.current.focus();
    }
  }, [isSending, isLoading]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || isSending || isLoading) return;

    setIsSending(true);
    try {
      await onSendMessage(inputMessage.trim());
      setInputMessage('');
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const formatMessageContent = (message: ChatMessage): string => {
    if (message.role === 'user') {
      return message.content;
    }

    // For assistant messages, highlight citations
    const citations: Citation[] = [];
    if (factCheckResults.length > 0) {
      factCheckResults.forEach(result => {
        citations.push(result.citation);
      });
    }

    return highlightCitations(message.content, citations, factCheckResults);
  };

  return (
    <div className="chat-container">
      {/* Messages */}
      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full" style={{color: '#6b7280'}}>
            <div className="text-center">
              <Bot className="w-16 h-16 mx-auto mb-4" style={{opacity: 0.5}} />
              <p className="text-lg">Start a conversation about academic topics</p>
              <p className="text-sm">Citations will be automatically fact-checked</p>
            </div>
          </div>
        ) : (
          messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`chat-message ${message.role === 'user' ? 'user' : 'assistant'}`}
              >
                <div className="flex items-start space-x-2 p-3">
                  <div className="flex-shrink-0">
                    {message.role === 'user' ? (
                      <User className="w-5 h-5 text-white" />
                    ) : (
                      <Bot className="w-5 h-5" style={{color: 'var(--primary-500)'}} />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div
                      dangerouslySetInnerHTML={{
                        __html: formatMessageContent(message)
                      }}
                    />
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
        {(isSending || isLoading) && (
          <div className="flex justify-start">
            <div className="chat-message assistant" style={{maxWidth: '80%'}}>
              <div className="flex items-center space-x-2 p-3">
                <Loader2 className="w-5 h-5 loading-spinner" />
                <span style={{color: '#6b7280'}}>
                  {isSending ? 'Sending...' : 'Processing...'}
                </span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <div className="chat-input">
        <form onSubmit={handleSubmit} className="flex space-x-2">
          <div className="flex-1">
            <textarea
              ref={inputRef}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about academic topics..."
              className="textarea"
              rows={3}
              disabled={isSending || isLoading}
            />
          </div>
          <button
            type="submit"
            disabled={!inputMessage.trim() || isSending || isLoading}
            className="btn btn-primary flex items-center space-x-2 self-end"
          >
            <Send className="w-4 h-4" />
            <span>Send</span>
          </button>
        </form>
      </div>
    </div>
  );
};