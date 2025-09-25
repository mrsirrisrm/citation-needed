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
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-primary-500" />
          <p className="text-gray-600 dark:text-gray-400">Initializing Citation Needed...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-3">
              <MessageSquare className="w-8 h-8 text-primary-500" />
              <div>
                <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
                  Citation Needed
                </h1>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Chat with AI and get automatic fact-checking
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-4">
              <button
                onClick={handleClear}
                className="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              >
                Clear Chat
              </button>
              <button
                onClick={handleRefreshStats}
                className="p-1.5 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
                title="Refresh statistics"
              >
                <Loader2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto h-[calc(100vh-4rem)]">
        <div className="flex h-full">
          {/* Chat Area (2/3 width) */}
          <div className="flex-1 min-w-0">
            <Chat
              messages={messages}
              onSendMessage={handleSendMessage}
              isLoading={isLoading}
              factCheckResults={factCheckResults}
            />
          </div>

          {/* Side Panel (1/3 width) */}
          <div className="w-96 border-l border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
            <div className="h-full flex flex-col">
              {/* Tabs */}
              <div className="border-b border-gray-200 dark:border-gray-700">
                <nav className="flex -mb-px">
                  <button
                    onClick={() => setActiveTab('fact-check')}
                    className={`flex-1 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                      activeTab === 'fact-check'
                        ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                        : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                    }`}
                  >
                    <MessageSquare className="w-4 h-4 inline mr-2" />
                    Fact-Check
                  </button>
                  <button
                    onClick={() => setActiveTab('usage')}
                    className={`flex-1 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                      activeTab === 'usage'
                        ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                        : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                    }`}
                  >
                    <BarChart3 className="w-4 h-4 inline mr-2" />
                    Usage
                  </button>
                  <button
                    onClick={() => setActiveTab('status')}
                    className={`flex-1 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                      activeTab === 'status'
                        ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                        : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                    }`}
                  >
                    <Settings className="w-4 h-4 inline mr-2" />
                    Status
                  </button>
                </nav>
              </div>

              {/* Tab Content */}
              <div className="flex-1 overflow-y-auto">
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
                  <div className="p-4">
                    <UsageStatsPanel usageStats={usageStats} />
                  </div>
                )}

                {activeTab === 'status' && systemStatus && (
                  <div className="p-4">
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
