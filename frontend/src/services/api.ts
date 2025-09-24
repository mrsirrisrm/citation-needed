import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Types
export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatRequest {
  message: string;
  history?: ChatMessage[];
}

export interface ChatResponse {
  response: string;
  citations: Citation[];
  task_id?: string;
}

export interface Citation {
  text: string;
  start: number;
  end: number;
  type: string;
  confidence: number;
}

export interface TaskStatus {
  status: string;
  progress: number;
  completed: boolean;
  error?: string;
  result?: {
    fact_check_results: FactCheckResult[];
  };
  partial_panel?: string;
  has_partial: boolean;
}

export interface FactCheckResult {
  citation: Citation;
  verification_status: 'verified' | 'not_found' | 'contradicted' | 'error' | 'partial';
  explanation: string;
  confidence: number;
  sources_found: Source[];
}

export interface Source {
  title: string;
  url: string;
  content?: string;
}

export interface SystemStatus {
  chat_model: boolean;
  search_client: boolean;
  ner_extractor: boolean;
  fact_checker: boolean;
  search_backend: string;
  active_tasks: number;
}

export interface UsageStats {
  total_calls: number;
  total_cost_usd: number;
  successful_calls: number;
  total_tokens: number;
  success_rate: number;
  avg_duration: number;
  provider_breakdown?: Record<string, any>;
  top_endpoints?: Array<{
    endpoint: string;
    calls: number;
  }>;
}

// API Functions
export const chatApi = {
  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    const response = await api.post('/chat', request);
    return response.data;
  },

  async getTaskStatus(taskId: string): Promise<TaskStatus> {
    const response = await api.get(`/task/${taskId}`);
    return response.data;
  },

  async getSystemStatus(): Promise<SystemStatus> {
    const response = await api.get('/system/status');
    return response.data;
  },

  async getUsageStats(): Promise<UsageStats> {
    const response = await api.get('/usage/stats');
    return response.data;
  },

  async healthCheck(): Promise<{ status: string; timestamp: number }> {
    const response = await api.get('/health');
    return response.data;
  },
};

// Polling utility for async tasks
export class TaskPoller {
  private pollInterval: number = 2000; // 2 seconds
  private timeout: number = 60000; // 60 seconds
  private timeoutId?: NodeJS.Timeout;
  private intervalId?: NodeJS.Timeout;

  constructor(
    private taskId: string,
    private onProgress: (status: TaskStatus) => void,
    private onComplete: (result: FactCheckResult[]) => void,
    private onError: (error: string) => void
  ) {}

  start(): void {
    // Set timeout
    this.timeoutId = setTimeout(() => {
      this.stop();
      this.onError('Task timeout');
    }, this.timeout);

    // Start polling
    this.intervalId = setInterval(async () => {
      try {
        const status = await chatApi.getTaskStatus(this.taskId);
        this.onProgress(status);

        if (status.completed) {
          this.stop();
          if (status.result?.fact_check_results) {
            this.onComplete(status.result.fact_check_results);
          } else {
            this.onError('Task completed but no results found');
          }
        }
      } catch (error) {
        this.stop();
        this.onError(error instanceof Error ? error.message : 'Unknown error');
      }
    }, this.pollInterval);
  }

  stop(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = undefined;
    }
    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
      this.timeoutId = undefined;
    }
  }
}

// Utility functions
export function highlightCitations(text: string, citations: Citation[], factCheckResults?: FactCheckResult[]): string {
  if (!citations.length) return text;

  // Create mapping of citations to fact-check results
  const resultMap = new Map<string, FactCheckResult>();
  if (factCheckResults) {
    factCheckResults.forEach(result => {
      const key = `${result.citation.start}_${result.citation.end}`;
      resultMap.set(key, result);
    });
  }

  // Sort citations by start position (reverse order for processing)
  const sortedCitations = [...citations].sort((a, b) => b.start - a.start);

  let highlightedText = text;

  // Process citations from end to start to maintain positions
  sortedCitations.forEach((citation, index) => {
    const citationId = `citation_${index + 1}`;
    const key = `${citation.start}_${citation.end}`;
    const factResult = resultMap.get(key);

    const statusClass = factResult ? getStatusClass(factResult.verification_status) : '';

    const highlightHtml = `<span class="citation-highlight ${statusClass}" id="${citationId}" data-citation-id="${citationId}" title="Click to see fact-check details">${escapeHtml(citation.text)}</span>`;

    highlightedText =
      highlightedText.slice(0, citation.start) +
      highlightHtml +
      highlightedText.slice(citation.end);
  });

  return highlightedText;
}

export function getStatusClass(status: string): string {
  const statusClasses = {
    verified: 'citation-verified',
    not_found: 'citation-not-found',
    contradicted: 'citation-contradicted',
    error: 'citation-error',
    partial: 'citation-not-found',
  };
  return statusClasses[status as keyof typeof statusClasses] || 'citation-error';
}

export function getStatusDisplay(status: string): string {
  const statusDisplays = {
    verified: 'Verified',
    not_found: 'Not Found',
    contradicted: 'Contradicted',
    error: 'Error',
    partial: 'Partial',
  };
  return statusDisplays[status as keyof typeof statusDisplays] || 'Unknown';
}

export function escapeHtml(text: string): string {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

export default api;