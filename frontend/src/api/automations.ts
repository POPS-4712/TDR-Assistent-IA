/**
 * Automations API endpoints
 */

import { api } from './client';
import type {
  Automation,
  AutomationListResponse,
  AutomationDetailResponse,
  InstallAutomationResult,
  AutomationPreflightResult,
  AutomationAccountResolution,
  AutomationCredentialMapping,
  Execution,
  RunAutomationResult,
  EnableAutomationResult,
  DisableAutomationResult,
  UninstallAutomationResult,
  AutomationLogsResponse,
  UpdateCheckResponse,
} from '../types';

export async function listAutomations(): Promise<AutomationListResponse> {
  const response = await api.get<AutomationListResponse>('/automations');
  return response.data;
}

export async function discoverAutomations(): Promise<AutomationListResponse> {
  const response = await api.get<AutomationListResponse>('/automations/discover');
  return response.data;
}

export async function getAutomation(automationId: string): Promise<Automation> {
  const response = await api.get<AutomationDetailResponse>(`/automations/${automationId}`);
  return response.data.automation;
}

export async function preflightAllAutomations(): Promise<{ automations: AutomationPreflightResult[]; total: number; mutations_applied: false }> {
  const response = await api.post<{ automations: AutomationPreflightResult[]; total: number; mutations_applied: false }>('/automations/preflight', {});
  return response.data;
}

export async function preflightAutomation(automationId: string): Promise<AutomationPreflightResult> {
  const response = await api.post<AutomationPreflightResult>(`/automations/${automationId}/preflight`, {});
  return response.data;
}

export async function resolveAutomationAccounts(automationId: string): Promise<{
  automation_id: string;
  accounts: AutomationAccountResolution[];
  credential_mappings: AutomationCredentialMapping[];
  missing_requirements: string[];
  ready: boolean;
}> {
  const response = await api.get<{
    automation_id: string;
    accounts: AutomationAccountResolution[];
    credential_mappings: AutomationCredentialMapping[];
    missing_requirements: string[];
    ready: boolean;
  }>(`/automations/${automationId}/accounts`);
  return response.data;
}

export async function installAutomation(automationId: string): Promise<InstallAutomationResult> {
  const response = await api.post<InstallAutomationResult>(`/automations/${automationId}/install`, {});
  return response.data;
}

export async function runAutomation(automationId: string, profileId?: string | null): Promise<RunAutomationResult> {
  const response = await api.post<RunAutomationResult>(`/automations/${automationId}/run`, {
    profile_id: profileId ?? null,
  });
  return response.data;
}

export async function refreshExecution(executionId: string): Promise<Execution> {
  const response = await api.get<Execution>(`/automations/executions/${executionId}`);
  return response.data;
}

export async function enableAutomation(automationId: string): Promise<EnableAutomationResult> {

  const response = await api.post<EnableAutomationResult>(`/automations/${automationId}/enable`, {});
  return response.data;
}

export async function disableAutomation(automationId: string): Promise<DisableAutomationResult> {
  const response = await api.post<DisableAutomationResult>(`/automations/${automationId}/disable`, {});
  return response.data;
}

export async function uninstallAutomation(automationId: string): Promise<UninstallAutomationResult> {
  const response = await api.delete<UninstallAutomationResult>(`/automations/${automationId}`);
  return response.data;
}

export async function getAutomationLogs(
  automationId: string,
  limit = 50
): Promise<AutomationLogsResponse> {
  const response = await api.get<AutomationLogsResponse>(`/automations/${automationId}/logs`, {
    params: { limit },
  });
  return response.data;
}

export async function checkForUpdates(): Promise<UpdateCheckResponse> {
  const response = await api.get<UpdateCheckResponse>('/automations/updates/check');
  return response.data;
}