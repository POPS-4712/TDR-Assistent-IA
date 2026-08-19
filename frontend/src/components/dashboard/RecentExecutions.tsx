/**
 * Recent Executions component for Dashboard
 */

import { STATUS_COLORS, STATUS_LABELS } from '../../types';
import type { Execution } from '../../types';

interface RecentExecutionsProps {
  executions: Execution[];
}

export function RecentExecutions({ executions }: RecentExecutionsProps) {
  const recentExecutions = executions.slice(0, 5);

  if (recentExecutions.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <h3 className="text-sm font-medium text-gray-900 mb-4">Recent Executions</h3>
        <div className="text-center py-8">
          <p className="text-gray-500">No executions yet</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h3 className="text-sm font-medium text-gray-900 mb-4">Recent Executions</h3>
      <div className="space-y-3">
        {recentExecutions.map((execution) => (
          <div key={execution.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center space-x-3 min-w-0">
              <div className={`w-2 h-2 rounded-full ${STATUS_COLORS[execution.status] || STATUS_COLORS.unknown}`} />
              <div className="min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {execution.automation_id}
                </p>
                <p className="text-xs text-gray-500">
                  Started: {new Date(execution.started_at).toLocaleString()}
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <span className={`px-2 py-1 text-xs font-medium rounded-full ${STATUS_COLORS[execution.status] || STATUS_COLORS.unknown}`}>
                {STATUS_LABELS[execution.status] || execution.status}
              </span>
              {execution.completed_at && (
                <span className="text-xs text-gray-500">
                  {Math.round((new Date(execution.completed_at).getTime() - new Date(execution.started_at).getTime()) / 1000)}s
                </span>
              )}
              {execution.error_message && (
                <span className="text-xs text-red-600 truncate max-w-xs" title={execution.error_message}>
                  {execution.error_message}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}