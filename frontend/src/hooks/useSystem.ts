/**
 * Hook for system health, diagnostics, first-run state and optional local controls.
 */

import { useState, useCallback, useEffect } from 'react';
import { ApiError } from '../api/client';
import * as systemApi from '../api/system';
import type {
  ServiceControlResult,
  SetupStatus,
  SystemConfig,
  SystemDiagnostics,
  SystemStatus,
} from '../types';

export interface UseSystemState {
  systemStatus: SystemStatus | null;
  systemConfig: SystemConfig | null;
  setupStatus: SetupStatus | null;
  diagnostics: SystemDiagnostics | null;
  isLoading: boolean;
  error: ApiError | null;
}

export interface UseSystemActions {
  loadSystemStatus: () => Promise<void>;
  loadSystemConfig: () => Promise<void>;
  loadSetupStatus: () => Promise<void>;
  loadDiagnostics: () => Promise<void>;
  checkHealth: () => Promise<{ healthy: boolean; services: Record<string, { status: string; error?: string }> }>;
  completeSetup: () => Promise<boolean>;
  controlService: (service: 'backend' | 'postgres' | 'n8n' | 'playwright' | 'frontend', action: 'start' | 'stop' | 'restart') => Promise<ServiceControlResult | null>;
  refreshAll: () => Promise<void>;
  clearError: () => void;
}

export type UseSystemReturn = UseSystemState & UseSystemActions;

export function useSystem(): UseSystemReturn {
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [systemConfig, setSystemConfig] = useState<SystemConfig | null>(null);
  const [setupStatus, setSetupStatus] = useState<SetupStatus | null>(null);
  const [diagnostics, setDiagnostics] = useState<SystemDiagnostics | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const clearError = useCallback(() => setError(null), []);

  const loadSystemStatus = useCallback(async () => {
    try {
      const status = await systemApi.getSystemStatus();
      setSystemStatus(status);
    } catch (err) {
      setError(err instanceof ApiError ? err : ApiError.networkError(String(err)));
    }
  }, []);

  const loadSystemConfig = useCallback(async () => {
    try {
      const config = await systemApi.getSystemConfig();
      setSystemConfig(config);
    } catch (err) {
      setError(err instanceof ApiError ? err : ApiError.networkError(String(err)));
    }
  }, []);

  const loadSetupStatus = useCallback(async () => {
    try {
      const setup = await systemApi.getSetupStatus();
      setSetupStatus(setup);
    } catch (err) {
      setError(err instanceof ApiError ? err : ApiError.networkError(String(err)));
    }
  }, []);

  const loadDiagnostics = useCallback(async () => {
    try {
      const nextDiagnostics = await systemApi.getSystemDiagnostics();
      setDiagnostics(nextDiagnostics);
    } catch (err) {
      setError(err instanceof ApiError ? err : ApiError.networkError(String(err)));
    }
  }, []);

  const refreshAll = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [status, config, setup, nextDiagnostics] = await Promise.all([
        systemApi.getSystemStatus(),
        systemApi.getSystemConfig(),
        systemApi.getSetupStatus(),
        systemApi.getSystemDiagnostics(),
      ]);
      setSystemStatus(status);
      setSystemConfig(config);
      setSetupStatus(setup);
      setDiagnostics(nextDiagnostics);
    } catch (err) {
      setError(err instanceof ApiError ? err : ApiError.networkError(String(err)));
    } finally {
      setIsLoading(false);
    }
  }, []);

  const checkHealth = useCallback(async () => {
    setError(null);
    try {
      return await systemApi.checkSystemHealth();
    } catch (err) {
      const apiError = err instanceof ApiError ? err : ApiError.networkError(String(err));
      setError(apiError);
      return { healthy: false, services: {} };
    }
  }, []);

  const completeSetup = useCallback(async () => {
    setError(null);
    try {
      const result = await systemApi.completeSetup();
      if (result.success) await refreshAll();
      return result.success;
    } catch (err) {
      setError(err instanceof ApiError ? err : ApiError.networkError(String(err)));
      return false;
    }
  }, [refreshAll]);

  const controlService = useCallback(async (
    service: 'backend' | 'postgres' | 'n8n' | 'playwright' | 'frontend',
    action: 'start' | 'stop' | 'restart',
  ) => {
    setError(null);
    try {
      const result = await systemApi.controlService(service, action);
      await refreshAll();
      return result;
    } catch (err) {
      setError(err instanceof ApiError ? err : ApiError.networkError(String(err)));
      return null;
    }
  }, [refreshAll]);

  useEffect(() => {
    void refreshAll();
  }, [refreshAll]);

  return {
    systemStatus,
    systemConfig,
    setupStatus,
    diagnostics,
    isLoading,
    error,
    loadSystemStatus,
    loadSystemConfig,
    loadSetupStatus,
    loadDiagnostics,
    checkHealth,
    completeSetup,
    controlService,
    refreshAll,
    clearError,
  };
}
