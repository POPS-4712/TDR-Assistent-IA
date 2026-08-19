/**
 * Executions API endpoints
 */

import { api } from './client';
import type {
  Execution,
  ExecutionListResponse,
  ExecutionDetailResponse,
  RerunExecutionResponse,
} from '../types';

export async function listExecutions(params?: {
  automation_id?: string;
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<ExecutionListResponse> {
  const response = await api.get<ExecutionListResponse>('/executions', { params });
  return response.data;
}

export async function getExecution(executionId: string): Promise<Execution> {
  const response = await api.get<ExecutionDetailResponse>(`/executions/${executionId}`);
  return response.data.execution;
}

export async function rerunExecution(executionId: string): Promise<RerunExecutionResponse> {
  const response = await api.post<RerunExecutionResponse>(`/executions/${executionId}/rerun`, {});
  return response.data;
}