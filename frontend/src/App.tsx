import React, { useState, useEffect, useCallback } from 'react';
import { Chat, FactCheckPanel, SystemStatusPanel, UsageStatsPanel } from './components';
import {
  type ChatMessage,
  type ChatRequest,
  type ChatResponse,
  type FactCheckResult,
  type TaskStatus,
  type SystemStatus,
  type UsageStats,
  chatApi,
  TaskPoller
} from './services/api';
import { MessageSquare, BarChart3, Settings, Loader2 } from 'lucide-react';

type TabType = 'fact-check' | 'usage' | 'status';

function App() {
  // State
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [factCheckResults, setFactCheckResults] = useState<FactCheckResult[]>([]);
  const [currentTaskId, setCurrentTaskId] = useState<string | undefined>();
  const [taskStatus, setTaskStatus] = useState<TaskStatus | undefined>();
  const [activeTab, setActiveTab] = useState<TabType>('fact-check');
  const [activeCitationId, setActiveCitationId] = useState<string | undefined>();
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [usageStats, setUsageStats] = useState<UsageStats | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);

  // Initialize system status and usage stats
  useEffect(() => {
    const initializeSystem = async () => {
      try {
        const [status, stats] = await Promise.all([
          chatApi.getSystemStatus(),
          chatApi.getUsageStats()
        ]);
        setSystemStatus(status);
        setUsageStats(stats);
      } catch (error) {
        console.error('Error initializing system:', error);
      } finally {
        setIsInitializing(false);
      }
    };

    initializeSystem();
  }, []);

  // Handle sending a message
  const handleSendMessage = useCallback(async (message: string) => {
    if (!message.trim()) return;

    // Add user message to chat
    const userMessage: ChatMessage = { role: 'user', content: message };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    // Clear previous fact-check results
    setFactCheckResults([]);
    setCurrentTaskId(undefined);
    setTaskStatus(undefined);

    try {
      // Prepare chat history
      const chatHistory: ChatMessage[] = messages.filter(msg => msg.role !== 'system');

      const request: ChatRequest = {
        message,
        history: chatHistory
      };

      // Send message to backend
      const response: ChatResponse = await chatApi.sendMessage(request);

      // Add assistant response to chat
      const assistantMessage: ChatMessage = { role: 'assistant', content: response.response };
      setMessages(prev => [...prev, assistantMessage]);

      // Handle fact-checking task
      if (response.task_id && response.citations.length > 0) {
        setCurrentTaskId(response.task_id);

        // Start polling for task status
        const poller = new TaskPoller(
          response.task_id,
          (status: TaskStatus) => {
            setTaskStatus(status);
          },
          (results: FactCheckResult[]) => {
            setFactCheckResults(results);
            setCurrentTaskId(undefined);
            setTaskStatus(undefined);
          },
          (error: string) => {
            console.error('Task polling error:', error);
            setCurrentTaskId(undefined);
            setTaskStatus(undefined);
          }
        );

        poller.start();
      }
    } catch (error) {
      console.error('Error sending message:', error);

      // Add error message
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: `Error: ${error instanceof Error ? error.message : 'Unknown error occurred'}`
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, [messages]);

  // Handle citation click
  const handleCitationClick = useCallback((citationId: string) => {
    setActiveCitationId(citationId);

    // Scroll to citation in chat
    const citationElement = document.getElementById(citationId);
    if (citationElement) {
      citationElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
      citationElement.classList.add('ring-2', 'ring-primary-500');

      // Remove highlight after 2 seconds
      setTimeout(() => {
        citationElement.classList.remove('ring-2', 'ring-primary-500');
      }, 2000);
    }
  }, []);

  // Clear conversation
  const handleClear = useCallback(() => {
    setMessages([]);
    setFactCheckResults([]);
    setCurrentTaskId(undefined);
    setTaskStatus(undefined);
    setActiveCitationId(undefined);
  }, []);

  // Refresh stats
  const handleRefreshStats = useCallback(async () => {
    try {
      const [status, stats] = await Promise.all([
        chatApi.getSystemStatus(),
        chatApi.getUsageStats()
      ]);
      setSystemStatus(status);
      setUsageStats(stats);
    } catch (error) {
      console.error('Error refreshing stats:', error);
    }
  }, []);

  if (isInitializing) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center">
        <div className="text-center bg-white rounded-2xl p-8 shadow-xl">
          <div className="p-4 bg-primary-50 rounded-full w-20 h-20 mx-auto mb-6 flex items-center justify-center">
            <Loader2 className="w-10 h-10 animate-spin text-primary-500" />
          </div>
          <h2 className="text-xl font-semibold text-slate-900 mb-2">Starting up...</h2>
          <p className="text-slate-600">Initializing Citation Needed components</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Modern Header */}
      <header className="header">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-4">
              <div className="p-2 bg-white bg-opacity-20 rounded-xl backdrop-blur-sm">
                <MessageSquare className="w-8 h-8 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">
                  Citation Needed
                </h1>
                <p className="text-primary-100 text-sm font-medium">
                  AI Chat with Intelligent Fact-Checking
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <button
                onClick={handleClear}
                className="btn btn-secondary text-slate-700 bg-white bg-opacity-90 hover:bg-opacity-100"
              >
                Clear Chat
              </button>
              <button
                onClick={handleRefreshStats}
                className="p-2 text-white hover:bg-white hover:bg-opacity-20 rounded-lg transition-all duration-200"
                title="Refresh statistics"
              >
                <Loader2 className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto h-[calc(100vh-7rem)] p-2">
        <div className="main-layout">
          {/* Chat Area (2/3 width) */}
          <div className="chat-area">
            <Chat
              messages={messages}
              onSendMessage={handleSendMessage}
              isLoading={isLoading}
              factCheckResults={factCheckResults}
            />
          </div>

          {/* Side Panel (1/3 width) */}
          <div className="side-panel">
            <div className="h-full flex flex-col">
              {/* Modern Tabs */}
              <div className="tabs">
                <nav className="flex -mb-px">
                  <button
                    onClick={() => setActiveTab('fact-check')}
                    className={`tab-button ${activeTab === 'fact-check' ? 'active' : ''}`}
                  >
                    <MessageSquare className="w-4 h-4 inline mr-2" />
                    Fact-Check
                  </button>
                  <button
                    onClick={() => setActiveTab('usage')}
                    className={`tab-button ${activeTab === 'usage' ? 'active' : ''}`}
                  >
                    <BarChart3 className="w-4 h-4 inline mr-2" />
                    Usage
                  </button>
                  <button
                    onClick={() => setActiveTab('status')}
                    className={`tab-button ${activeTab === 'status' ? 'active' : ''}`}
                  >
                    <Settings className="w-4 h-4 inline mr-2" />
                    Status
                  </button>
                </nav>
              </div>

              {/* Tab Content */}
              <div className="flex-1 overflow-y-auto scrollbar-thin">
                {activeTab === 'fact-check' && (
                  <FactCheckPanel
                    taskId={currentTaskId}
                    factCheckResults={factCheckResults}
                    taskStatus={taskStatus}
                    onCitationClick={handleCitationClick}
                    activeCitationId={activeCitationId}
                  />
                )}

                {activeTab === 'usage' && usageStats && (
                  <div className="p-6">
                    <UsageStatsPanel usageStats={usageStats} />
                  </div>
                )}

                {activeTab === 'status' && systemStatus && (
                  <div className="p-6">
                    <SystemStatusPanel status={systemStatus} />
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
