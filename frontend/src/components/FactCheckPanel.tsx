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
        return <CheckCircle className="w-4 h-4 text-white" />;
      case 'not_found':
        return <XCircle className="w-4 h-4 text-white" />;
      case 'contradicted':
        return <XCircle className="w-4 h-4 text-white" />;
      case 'error':
        return <AlertTriangle className="w-4 h-4 text-slate-700" />;
      case 'partial':
        return <Clock className="w-4 h-4 text-primary-500" />;
      default:
        return <AlertTriangle className="w-4 h-4 text-slate-500" />;
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
        <div className="flex items-center justify-center mb-6">
          <div className="loading-spinner mr-3" />
          <h3 className="text-lg font-semibold text-slate-900">
            Fact-checking in progress...
          </h3>
        </div>

        {/* Progress bar */}
        <div className="progress-bar h-3 mb-4">
          <div
            className="progress-bar-fill h-full"
            style={{ width: `${taskStatus.progress * 100}%` }}
          />
        </div>

        <p className="text-sm text-slate-600 text-center font-medium">
          {Math.round(taskStatus.progress * 100)}% complete
        </p>

        {/* Show partial results if available */}
        {taskStatus.has_partial && taskStatus.partial_panel && (
          <div className="mt-6 border-t border-slate-200 pt-6">
            <h4 className="text-sm font-semibold text-slate-900 mb-4 flex items-center">
              <Clock className="w-4 h-4 mr-2 text-primary-500" />
              Partial Results
            </h4>
            <div
              className="text-sm text-slate-700"
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
      <div className="fact-check-panel p-8">
        <div className="text-center text-slate-500">
          <div className="p-4 bg-slate-100 rounded-full w-20 h-20 mx-auto mb-6 flex items-center justify-center">
            <Search className="w-10 h-10 text-slate-400" />
          </div>
          <h3 className="text-lg font-semibold mb-2 text-slate-900">No citations detected</h3>
          <p className="text-sm text-slate-600 leading-relaxed">
            Academic citations will be automatically fact-checked and appear here when you mention papers, studies, or research.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="p-6 border-b border-slate-200">
        <h3 className="text-lg font-semibold text-slate-900 flex items-center">
          <div className="p-2 bg-primary-100 rounded-lg mr-3">
            <Search className="w-5 h-5 text-primary-600" />
          </div>
          <div>
            <div className="flex items-center">
              Fact-Check Results
              {factCheckResults.length > 0 && (
                <span className="ml-2 px-2 py-1 text-xs font-medium bg-primary-100 text-primary-700 rounded-full">
                  {factCheckResults.length}
                </span>
              )}
            </div>
            <p className="text-sm text-slate-600 mt-1">Citation verification results</p>
          </div>
        </h3>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-4">
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
                  <div className="comment-citation-text text-sm font-semibold text-slate-900 mb-3 leading-relaxed">
                    {escapeHtml(result.citation.text.length > 60
                      ? result.citation.text.substring(0, 57) + '...'
                      : result.citation.text
                    )}
                  </div>
                  <div className="comment-status flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="flex items-center space-x-2">
                        {getStatusIcon(result.verification_status)}
                        <span className={`status-badge ${getStatusClass(result.verification_status)}`}>
                          {getStatusDisplay(result.verification_status)}
                        </span>
                      </div>
                      <div className="text-xs font-medium text-slate-500 bg-slate-100 px-2 py-1 rounded-md">
                        {Math.round(result.confidence * 100)}% confidence
                      </div>
                    </div>
                    <div className="flex items-center text-slate-400">
                      {isExpanded ? (
                        <ChevronUp className="w-5 h-5" />
                      ) : (
                        <ChevronDown className="w-5 h-5" />
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {isExpanded && (
                <div className="comment-content">
                  <div className="comment-explanation text-sm text-slate-700 mb-4 leading-relaxed bg-slate-50 p-4 rounded-lg">
                    {result.explanation}
                  </div>

                  {result.sources_found.length > 0 && (
                    <div className="comment-sources">
                      <div className="sources-title text-sm font-semibold text-slate-900 mb-4 flex items-center">
                        <ExternalLink className="w-4 h-4 mr-2 text-primary-500" />
                        Sources Found ({result.sources_found.length})
                      </div>
                      <div className="space-y-3">
                        {result.sources_found.slice(0, 3).map((source, sourceIndex) => (
                          <div key={sourceIndex} className="source-item">
                            <a
                              href={source.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="source-title font-semibold text-primary-600 hover:text-primary-700 flex items-center space-x-2 mb-2"
                            >
                              <span className="flex-1 truncate">
                                {escapeHtml(source.title.length > 50
                                  ? source.title.substring(0, 47) + '...'
                                  : source.title
                                )}
                              </span>
                              <ExternalLink className="w-4 h-4 flex-shrink-0" />
                            </a>
                            <div className="source-url text-xs text-slate-500 font-mono break-all bg-slate-100 p-2 rounded">
                              {source.url}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};