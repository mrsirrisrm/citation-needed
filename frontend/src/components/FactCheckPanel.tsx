import React, { useState } from 'react';
import { ChevronDown, ChevronUp, ExternalLink, Search, CheckCircle, XCircle, AlertTriangle, Clock } from 'lucide-react';
import { type FactCheckResult, type TaskStatus } from '../services/api';
import { getStatusClass, getStatusDisplay, escapeHtml } from '../services/api';

interface FactCheckPanelProps {
  taskId?: string;
  factCheckResults: FactCheckResult[];
  taskStatus?: TaskStatus;
  onCitationClick?: (citationId: string) => void;
  activeCitationId?: string;
}

export const FactCheckPanel: React.FC<FactCheckPanelProps> = ({
  taskId,
  factCheckResults,
  taskStatus,
  onCitationClick,
  activeCitationId
}) => {
  const [expandedComments, setExpandedComments] = useState<Set<string>>(new Set());

  const toggleComment = (citationId: string) => {
    const newExpanded = new Set(expandedComments);
    if (newExpanded.has(citationId)) {
      newExpanded.delete(citationId);
    } else {
      newExpanded.add(citationId);
      // Scroll to citation if available
      if (onCitationClick) {
        onCitationClick(citationId);
      }
    }
    setExpandedComments(newExpanded);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'verified':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'not_found':
        return <XCircle className="w-4 h-4 text-yellow-500" />;
      case 'contradicted':
        return <XCircle className="w-4 h-4 text-red-500" />;
      case 'error':
        return <AlertTriangle className="w-4 h-4 text-gray-500" />;
      case 'partial':
        return <Clock className="w-4 h-4 text-blue-500" />;
      default:
        return <AlertTriangle className="w-4 h-4 text-gray-500" />;
    }
  };

  const formatPartialPanel = (partialPanel: string) => {
    // This is a fallback - ideally we'd parse the HTML more safely
    return { __html: partialPanel };
  };

  // Show loading state if task is in progress
  if (taskStatus && !taskStatus.completed && taskId) {
    return (
      <div className="fact-check-panel p-6">
        <div className="flex items-center justify-center mb-4">
          <div className="loading-spinner mr-3" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Fact-checking in progress...
          </h3>
        </div>

        {/* Progress bar */}
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 mb-4">
          <div
            className="bg-primary-500 h-2 rounded-full transition-all duration-300"
            style={{ width: `${taskStatus.progress * 100}%` }}
          />
        </div>

        <p className="text-sm text-gray-600 dark:text-gray-400 text-center">
          {Math.round(taskStatus.progress * 100)}% complete
        </p>

        {/* Show partial results if available */}
        {taskStatus.has_partial && taskStatus.partial_panel && (
          <div className="mt-4 border-t border-gray-200 dark:border-gray-700 pt-4">
            <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-3">
              Partial Results
            </h4>
            <div
              className="text-sm"
              dangerouslySetInnerHTML={formatPartialPanel(taskStatus.partial_panel)}
            />
          </div>
        )}
      </div>
    );
  }

  // Show empty state if no results
  if (factCheckResults.length === 0 && !taskId) {
    return (
      <div className="fact-check-panel p-6">
        <div className="text-center text-gray-500 dark:text-gray-400">
          <Search className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p className="text-lg font-medium mb-1">No citations detected</p>
          <p className="text-sm">
            Academic citations will be automatically fact-checked and appear here.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="fact-check-panel p-4 max-h-[80vh] overflow-y-auto scrollbar-thin">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
        <Search className="w-5 h-5 mr-2" />
        Fact-Check Results
        {factCheckResults.length > 0 && (
          <span className="ml-2 text-sm text-gray-500 dark:text-gray-400">
            ({factCheckResults.length})
          </span>
        )}
      </h3>

      <div className="space-y-3">
        {factCheckResults.map((result, index) => {
          const citationId = `citation_${index + 1}`;
          const isExpanded = expandedComments.has(citationId);
          const isActive = activeCitationId === citationId;

          return (
            <div
              key={citationId}
              className={`citation-comment transition-all duration-200 ${
                isActive ? 'ring-2 ring-primary-500' : ''
              }`}
            >
              <div
                className="comment-header cursor-pointer"
                onClick={() => toggleComment(citationId)}
              >
                <div className="flex-1 min-w-0">
                  <div className="comment-citation-text text-sm font-medium text-gray-900 dark:text-white mb-2">
                    {escapeHtml(result.citation.text.length > 60
                      ? result.citation.text.substring(0, 57) + '...'
                      : result.citation.text
                    )}
                  </div>
                  <div className="comment-status flex items-center space-x-2">
                    <div className="flex items-center space-x-1">
                      {getStatusIcon(result.verification_status)}
                      <span className={`status-badge ${getStatusClass(result.verification_status)}`}>
                        {getStatusDisplay(result.verification_status)}
                      </span>
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      {Math.round(result.confidence * 100)}% confidence
                    </div>
                    <div className="flex-1" />
                    {isExpanded ? (
                      <ChevronUp className="w-4 h-4 text-gray-500" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-gray-500" />
                    )}
                  </div>
                </div>
              </div>

              {isExpanded && (
                <div className="comment-content">
                  <div className="comment-explanation text-sm text-gray-700 dark:text-gray-300 mb-3">
                    {result.explanation}
                  </div>

                  {result.sources_found.length > 0 && (
                    <div className="comment-sources">
                      <div className="sources-title text-sm font-medium text-gray-900 dark:text-white mb-2">
                        Sources Found:
                      </div>
                      <div className="space-y-2">
                        {result.sources_found.slice(0, 3).map((source, sourceIndex) => (
                          <div key={sourceIndex} className="source-item">
                            <a
                              href={source.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="source-title font-medium text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300 flex items-center space-x-1"
                            >
                              <span className="flex-1 truncate">
                                {escapeHtml(source.title.length > 50
                                  ? source.title.substring(0, 47) + '...'
                                  : source.title
                                )}
                              </span>
                              <ExternalLink className="w-3 h-3 flex-shrink-0" />
                            </a>
                            <div className="source-url text-xs text-gray-500 dark:text-gray-400 font-mono">
                              {source.url}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="confidence-score text-xs text-gray-500 dark:text-gray-400 mt-3 text-right">
                    Confidence: {Math.round(result.confidence * 100)}%
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};