import React from 'react';
import {
  CheckCircle,
  XCircle,
  Activity,
  Bot,
  Search,
  Zap
} from 'lucide-react';
import { type SystemStatus } from '../services/api';

interface SystemStatusPanelProps {
  status: SystemStatus;
}

export const SystemStatusPanel: React.FC<SystemStatusPanelProps> = ({
  status
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

  return (
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
  );
};