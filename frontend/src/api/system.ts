/**
 * System API endpoints. All responses intentionally exclude secret values.
 */

import { api, ApiError } from './client';
import type {
  ServiceControlResult,
  SetupStatus,
  SystemConfig,
  SystemDiagnostics,
  SystemStatus,
} from '../types';

export async function getSystemStatus(): Promise<SystemStatus> {
  const response = await api.get<SystemStatus>('/system/status');
  return response.data;
}

export async function getSystemVersion(): Promise<{ version: string }> {
  const response = await api.get<{ version: string }>('/system/version');
  return response.data;
}

export async function getSystemConfig(): Promise<SystemConfig> {
  const response = await api.get<SystemConfig>('/system/config');
  return response.data;
}

export async function getSetupStatus(): Promise<SetupStatus> {
  const response = await api.get<SetupStatus>('/system/setup');
  return response.data;
}

export async function completeSetup(): Promise<{ success: boolean; first_run_complete: boolean }> {
  const response = await api.post<{ success: boolean; first_run_complete: boolean }>('/system/setup/complete', {});
  return response.data;
}

export async function getSystemDiagnostics(): Promise<SystemDiagnostics> {
  const response = await api.get<SystemDiagnostics>('/system/diagnostics');
  return response.data;
}

export async function controlService(
  service: 'backend' | 'postgres' | 'n8n' | 'playwright' | 'frontend',
  action: 'start' | 'stop' | 'restart',
): Promise<ServiceControlResult> {
  const response = await api.post<ServiceControlResult>(`/system/services/${service}/${action}`, {});
  return response.data;
}

export async function checkSystemHealth(): Promise<{
  healthy: boolean;
  services: Record<string, { status: string; error?: string }>;
}> {
  try {
    const status = await getSystemStatus();
    const allHealthy = Object.values(status.services).every(
      (service) => service.status === 'healthy'
    );
    return {
      healthy: allHealthy,
      services: status.services,
    };
  } catch (error) {
    if (error instanceof ApiError) {
      return {
        healthy: false,
        services: {},
      };
    }
    throw error;
  }
}
