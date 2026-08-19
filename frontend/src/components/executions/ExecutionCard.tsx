/**
 * Execution Card component for displaying execution details
 */

import { Execution } from '../../types';
import { STATUS_COLORS, STATUS_LABELS } from '../../types';

interface ExecutionCardProps {
  execution: Execution;
  automationName?: string;
  onViewDetails?: (execution: Execution) => void;
  onRerun?: (execution: Execution) => void;
}

export function ExecutionCard({ execution, automationName, onViewDetails, onRerun }: ExecutionCardProps) {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const formatDuration = (startedAt: string, completedAt?: string) => {
    if (!completedAt) return 'Running...';
    const start = new Date(startedAt).getTime();
    const end = new Date(completedAt).getTime();
    const ms = end - start;
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5 hover:border-gray-300 transition-colors">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center space-x-3">
            <h3 className="font-medium text-gray-900 truncate">{automationName || execution.automation_id}</h3>
            <span className={`px-2 py-1 text-xs font-medium rounded-full ${STATUS_COLORS[execution.status] || STATUS_COLORS.unknown}`}>
              {STATUS_LABELS[execution.status] || execution.status}
            </span>
          </div>
          <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-gray-500">Started</p>
              <p className="font-medium text-gray-900">{formatDate(execution.started_at)}</p>
            </div>
            <div>
              <p className="text-gray-500">Completed</p>
              <p className="font-medium text-gray-900">{execution.completed_at ? formatDate(execution.completed_at) : '—'}</p>
            </div>
            <div>
              <p className="text-gray-500">Duration</p>
              <p className="font-medium text-gray-900">{formatDuration(execution.started_at, execution.completed_at)}</p>
            </div>
            <div>
              <p className="text-gray-500">ID</p>
              <p className="font-medium text-gray-900 font-mono text-xs">{execution.id.slice(0, 8)}...</p>
            </div>
          </div>
          {execution.error_message && (
            <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-700">{execution.error_message}</p>
            </div>
          )}
        </div>
        <div className="flex items-center space-x-2 ml-4">
          {onViewDetails && (
            <button
              onClick={() => onViewDetails(execution)}
              className="px-3 py-1.5 text-sm text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
            >
              View Details
            </button>
          )}
          {onRerun && execution.status !== 'running' && (
            <button
              onClick={() => onRerun(execution)}
              className="px-3 py-1.5 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
            >
              Rerun
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
