import React from 'react';
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  Activity,
  Database,
  Bot,
  Search,
  Zap,
  BarChart3
} from 'lucide-react';
import { SystemStatus, UsageStats } from '../services/api';

interface SystemStatusPanelProps {
  status: SystemStatus;
  usageStats?: UsageStats;
}

export const SystemStatusPanel: React.FC<SystemStatusPanelProps> = ({
  status,
  usageStats
}) => {
  const getStatusIcon = (isWorking: boolean) => {
    return isWorking ? (
      <CheckCircle className="w-5 h-5 text-green-500" />
    ) : (
      <XCircle className="w-5 h-5 text-red-500" />
    );
  };

  const getStatusText = (isWorking: boolean) => {
    return isWorking ? 'Ready' : 'Error';
  };

  const getStatusClass = (isWorking: boolean) => {
    return isWorking ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400';
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('en-US').format(num);
  };

  return (
    <div className="space-y-6">
      {/* System Status */}
      <div className="fact-check-panel p-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
          <Activity className="w-5 h-5 mr-2" />
          System Status
        </h3>

        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div className="flex items-center space-x-3">
              <Bot className="w-5 h-5 text-gray-600 dark:text-gray-400" />
              <span className="text-sm font-medium text-gray-900 dark:text-white">
                Chat Model
              </span>
            </div>
            <div className={`flex items-center space-x-2 ${getStatusClass(status.chat_model)}`}>
              {getStatusIcon(status.chat_model)}
              <span className="text-sm font-medium">{getStatusText(status.chat_model)}</span>
            </div>
          </div>

          <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div className="flex items-center space-x-3">
              <Search className="w-5 h-5 text-gray-600 dark:text-gray-400" />
              <span className="text-sm font-medium text-gray-900 dark:text-white">
                Search Client
              </span>
            </div>
            <div className={`flex items-center space-x-2 ${getStatusClass(status.search_client)}`}>
              {getStatusIcon(status.search_client)}
              <span className="text-sm font-medium">{getStatusText(status.search_client)}</span>
            </div>
          </div>

          <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div className="flex items-center space-x-3">
              <Zap className="w-5 h-5 text-gray-600 dark:text-gray-400" />
              <span className="text-sm font-medium text-gray-900 dark:text-white">
                NER Extractor
              </span>
            </div>
            <div className={`flex items-center space-x-2 ${getStatusClass(status.ner_extractor)}`}>
              {getStatusIcon(status.ner_extractor)}
              <span className="text-sm font-medium">{getStatusText(status.ner_extractor)}</span>
            </div>
          </div>

          <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div className="flex items-center space-x-3">
              <CheckCircle className="w-5 h-5 text-gray-600 dark:text-gray-400" />
              <span className="text-sm font-medium text-gray-900 dark:text-white">
                Fact Checker
              </span>
            </div>
            <div className={`flex items-center space-x-2 ${getStatusClass(status.fact_checker)}`}>
              {getStatusIcon(status.fact_checker)}
              <span className="text-sm font-medium">{getStatusText(status.fact_checker)}</span>
            </div>
          </div>
        </div>

        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-600 dark:text-gray-400">Search Backend:</span>
              <span className="ml-2 font-medium text-gray-900 dark:text-white">
                {status.search_backend}
              </span>
            </div>
            <div>
              <span className="text-gray-600 dark:text-gray-400">Active Tasks:</span>
              <span className="ml-2 font-medium text-gray-900 dark:text-white">
                {status.active_tasks}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Usage Statistics */}
      {usageStats && (
        <div className="fact-check-panel p-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
            <BarChart3 className="w-5 h-5 mr-2" />
            Usage Statistics (Last 24 Hours)
          </h3>

          <div className="grid grid-cols-2 gap-4 mb-4">
            <div className="bg-blue-50 dark:bg-blue-900/20 p-3 rounded-lg">
              <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                {formatNumber(usageStats.total_calls)}
              </div>
              <div className="text-sm text-blue-600 dark:text-blue-400">Total Calls</div>
            </div>

            <div className="bg-green-50 dark:bg-green-900/20 p-3 rounded-lg">
              <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                {formatCurrency(usageStats.total_cost_usd)}
              </div>
              <div className="text-sm text-green-600 dark:text-green-400">Total Cost</div>
            </div>

            <div className="bg-purple-50 dark:bg-purple-900/20 p-3 rounded-lg">
              <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                {formatNumber(usageStats.successful_calls)}
              </div>
              <div className="text-sm text-purple-600 dark:text-purple-400">Successful</div>
            </div>

            <div className="bg-orange-50 dark:bg-orange-900/20 p-3 rounded-lg">
              <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">
                {formatNumber(usageStats.total_tokens)}
              </div>
              <div className="text-sm text-orange-600 dark:text-orange-400">Tokens Used</div>
            </div>
          </div>

          <div className="space-y-3 text-sm">
            <div className="flex justify-between items-center p-2 bg-gray-50 dark:bg-gray-700 rounded">
              <span className="text-gray-600 dark:text-gray-400">Success Rate:</span>
              <span className="font-medium text-gray-900 dark:text-white">
                {usageStats.success_rate.toFixed(1)}%
              </span>
            </div>

            <div className="flex justify-between items-center p-2 bg-gray-50 dark:bg-gray-700 rounded">
              <span className="text-gray-600 dark:text-gray-400">Avg Duration:</span>
              <span className="font-medium text-gray-900 dark:text-white">
                {usageStats.avg_duration.toFixed(2)}s
              </span>
            </div>
          </div>

          {/* Provider Breakdown */}
          {usageStats.provider_breakdown && Object.keys(usageStats.provider_breakdown).length > 0 && (
            <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
              <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
                Provider Breakdown
              </h4>
              <div className="space-y-2">
                {Object.entries(usageStats.provider_breakdown).map(([provider, stats]: [string, any]) => {
                  const successRate = (stats.successful_calls / Math.max(1, stats.calls)) * 100;
                  return (
                    <div key={provider} className="flex justify-between items-center text-xs">
                      <span className="font-medium text-gray-700 dark:text-gray-300 uppercase">
                        {provider}
                      </span>
                      <div className="flex items-center space-x-3">
                        <span className="text-gray-600 dark:text-gray-400">
                          {stats.calls} calls
                        </span>
                        <span className="text-green-600 dark:text-green-400">
                          {formatCurrency(stats.cost_usd)}
                        </span>
                        <span className="text-blue-600 dark:text-blue-400">
                          {successRate.toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Top Endpoints */}
          {usageStats.top_endpoints && usageStats.top_endpoints.length > 0 && (
            <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
              <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
                Top Endpoints
              </h4>
              <div className="space-y-2">
                {usageStats.top_endpoints.map((endpoint, index) => (
                  <div key={index} className="flex justify-between items-center text-xs">
                    <span className="text-gray-600 dark:text-gray-400">
                      {index + 1}. {endpoint.endpoint}
                    </span>
                    <span className="text-gray-600 dark:text-gray-400">
                      {endpoint.calls} calls
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};