/**
 * Hook for managing executions state and operations
 */

import { useState, useCallback, useEffect } from 'react';
import { ApiError } from '../api/client';
import * as executionsApi from '../api/executions';
import type { Execution, RerunExecutionResponse } from '../types';

export interface UseExecutionsState {
  executions: Execution[];
  isLoading: boolean;
  error: ApiError | null;
  selectedExecution: Execution | null;
  total: number;
  page: number;
  limit: number;
}

export interface UseExecutionsActions {
  loadExecutions: (params?: { automation_id?: string; status?: string; limit?: number; offset?: number }) => Promise<void>;
  selectExecution: (execution: Execution | null) => void;
  rerunExecution: (executionId: string) => Promise<RerunExecutionResponse | null>;
  refreshExecution: (executionId: string) => Promise<void>;
  setPage: (page: number) => void;
  setLimit: (limit: number) => void;
  clearError: () => void;
}

export type UseExecutionsReturn = UseExecutionsState & UseExecutionsActions;

export function useExecutions(): UseExecutionsReturn {
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [selectedExecution, setSelectedExecution] = useState<Execution | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(20);

  const clearError = useCallback(() => setError(null), []);

  const loadExecutions = useCallback(async (params?: { automation_id?: string; status?: string; limit?: number; offset?: number }) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await executionsApi.listExecutions({
        ...params,
        limit: params?.limit ?? limit,
        offset: params?.offset ?? (page - 1) * limit,
      });
      setExecutions(response.executions);
      setTotal(response.total);
    } catch (err) {
      const apiError = err instanceof ApiError ? err : ApiError.networkError(String(err));
      setError(apiError);
    } finally {
      setIsLoading(false);
    }
  }, [limit, page]);

  const selectExecution = useCallback((execution: Execution | null) => {
    setSelectedExecution(execution);
  }, []);

  const rerunExecution = useCallback(async (executionId: string): Promise<RerunExecutionResponse | null> => {
    setError(null);
    try {
      const result = await executionsApi.rerunExecution(executionId);
      // Reload executions to see the new one
      await loadExecutions();
      return result;
    } catch (err) {
      const apiError = err instanceof ApiError ? err : ApiError.networkError(String(err));
      setError(apiError);
      return null;
    }
  }, [loadExecutions]);

  const refreshExecution = useCallback(async (executionId: string) => {
    setError(null);
    try {
      const execution = await executionsApi.getExecution(executionId);
      setExecutions(prev => prev.map(e => e.id === executionId ? execution : e));
      if (selectedExecution?.id === executionId) {
        setSelectedExecution(execution);
      }
    } catch (err) {
      const apiError = err instanceof ApiError ? err : ApiError.networkError(String(err));
      setError(apiError);
    }
  }, [selectedExecution]);

  // Load on mount
  useEffect(() => {
    loadExecutions();
  }, [loadExecutions]);

  return {
    executions,
    isLoading,
    error,
    selectedExecution,
    total,
    page,
    limit,
    loadExecutions,
    selectExecution,
    rerunExecution,
    refreshExecution,
    setPage,
    setLimit,
    clearError,
  };
}