/**
 * Executions page for Automation Center
 */

import { useEffect, useState } from 'react';
import { useExecutions } from '../hooks/useExecutions';
import { useAutomations } from '../hooks/useAutomations';
import { ExecutionCard } from '../components/executions/ExecutionCard';
import { STATUS_COLORS, STATUS_LABELS } from '../types';

export function Executions() {
  const { 
    executions, 
    isLoading, 
    error, 
    loadExecutions,
    rerunExecution,
    clearError,
  } = useExecutions();

  const { automations } = useAutomations();

  const [selectedExecution, setSelectedExecution] = useState<typeof executions[0] | null>(null);
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    loadExecutions();
  }, [loadExecutions]);

  const handleViewDetails = (execution: typeof executions[0]) => {
    setSelectedExecution(execution);
    setShowDetails(true);
  };

  const handleRerun = async (execution: typeof executions[0]) => {
    try {
      await rerunExecution(execution.id);
      loadExecutions();
    } catch (err) {
      console.error('Failed to rerun execution:', err);
    }
  };

  const getAutomationName = (automationId: string) => {
    const automation = automations.find(a => a.id === automationId);
    return automation?.name || automationId;
  };

  const statusCounts = {
    active: executions.filter((execution) => ['queued', 'running'].includes(execution.status)).length,
    completed: executions.filter((execution) => execution.status === 'completed').length,
    failed: executions.filter((execution) => execution.status === 'failed').length,
    cancelled: executions.filter((execution) => execution.status === 'cancelled').length,
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Executions</h1>
          <p className="text-gray-500 mt-1">Monitor and manage automation executions</p>
        </div>
        <button
          onClick={() => loadExecutions()}
          disabled={isLoading}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors flex items-center space-x-2"
        >
          <svg className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          <span>{isLoading ? 'Refreshing...' : 'Refresh'}</span>
        </button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <svg className="w-5 h-5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <span className="text-red-700">{error.getUserMessage()}</span>
            </div>
            <button onClick={clearError} className="text-red-500 hover:text-red-700">
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* Status Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-sm text-gray-500">Active</p>
          <p className="text-2xl font-bold text-blue-600 mt-1">{statusCounts.active}</p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-sm text-gray-500">Completed</p>
          <p className="text-2xl font-bold text-green-600 mt-1">{statusCounts.completed}</p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-sm text-gray-500">Failed</p>
          <p className="text-2xl font-bold text-red-600 mt-1">{statusCounts.failed}</p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-sm text-gray-500">Cancelled</p>
          <p className="text-2xl font-bold text-gray-600 mt-1">{statusCounts.cancelled}</p>
        </div>
      </div>

      {/* Executions List */}
      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Executions</h2>
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <svg className="animate-spin h-8 w-8 text-blue-600" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
          </div>
        ) : executions.length === 0 ? (
          <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">No executions found</h3>
            <p className="mt-1 text-sm text-gray-500">Executions will appear here when automations run.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {executions.map((execution) => (
              <ExecutionCard
                key={execution.id}
                execution={execution}
                automationName={getAutomationName(execution.automation_id)}
                onViewDetails={handleViewDetails}
                onRerun={handleRerun}
              />
            ))}
          </div>
        )}
      </section>

      {/* Execution Details Modal */}
      {showDetails && selectedExecution && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4">
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" onClick={() => setShowDetails(false)} />
            <div className="relative bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-auto">
              <div className="flex items-center justify-between p-4 border-b">
                <h3 className="text-lg font-semibold text-gray-900">Execution Details</h3>
                <button onClick={() => setShowDetails(false)} className="text-gray-400 hover:text-gray-500">
                  <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <div className="p-4 space-y-4">
                <div className="flex items-center space-x-3">
                  <h4 className="font-medium text-gray-900">{getAutomationName(selectedExecution.automation_id)}</h4>
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${STATUS_COLORS[selectedExecution.status] || STATUS_COLORS.unknown}`}>
                    {STATUS_LABELS[selectedExecution.status] || selectedExecution.status}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-gray-500">Execution ID</p>
                    <p className="font-medium text-gray-900 font-mono">{selectedExecution.id}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Automation ID</p>
                    <p className="font-medium text-gray-900 font-mono">{selectedExecution.automation_id}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Started</p>
                    <p className="font-medium text-gray-900">{new Date(selectedExecution.started_at).toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Completed</p>
                    <p className="font-medium text-gray-900">{selectedExecution.completed_at ? new Date(selectedExecution.completed_at).toLocaleString() : '—'}</p>
                  </div>
                  {selectedExecution.n8n_execution_id && (
                    <div>
                      <p className="text-gray-500">n8n Execution ID</p>
                      <p className="font-medium text-gray-900 font-mono">{selectedExecution.n8n_execution_id}</p>
                    </div>
                  )}
                                    {selectedExecution.workflow_id && (
                    <div>
                      <p className="text-gray-500">Workflow ID</p>
                      <p className="font-medium text-gray-900 font-mono">{selectedExecution.workflow_id}</p>
                    </div>
                  )}
                  {selectedExecution.profile_id && (
                    <div>
                      <p className="text-gray-500">Profile ID</p>
                      <p className="font-medium text-gray-900 font-mono">{selectedExecution.profile_id}</p>
                    </div>
                  )}
                  <div>
                    <p className="text-gray-500">Duration</p>
                    <p className="font-medium text-gray-900">{selectedExecution.duration_ms !== undefined ? `${selectedExecution.duration_ms} ms` : '—'}</p>
                  </div>

                </div>
                {selectedExecution.error_message && (
                  <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                    <p className="text-sm font-medium text-red-700">Error</p>
                    <p className="text-sm text-red-600 mt-1">{selectedExecution.error_message}</p>
                  </div>
                )}
                                <div className="rounded-md bg-gray-50 p-3 text-sm text-gray-600">
                  Execution tracking stores status and timing metadata only. Runtime payloads are intentionally not displayed.
                </div>

              </div>
              <div className="flex justify-end space-x-3 p-4 border-t">
                <button
                  onClick={() => setShowDetails(false)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                >
                  Close
                </button>
                                {!['queued', 'running'].includes(selectedExecution.status) && (

                  <button
                    onClick={() => handleRerun(selectedExecution)}
                    className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    Rerun
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}