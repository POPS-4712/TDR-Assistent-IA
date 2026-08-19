/**
 * Hook for managing automation lifecycle state and automatic read-only preflight.
 */

import { useState, useCallback, useEffect } from 'react';
import { ApiError } from '../api/client';
import * as automationsApi from '../api/automations';
import type {
  Automation,
  AutomationPreflightResult,
  InstallAutomationResult,
  RunAutomationResult,
} from '../types';

export interface UseAutomationsState {
  automations: Automation[];
  preflightById: Record<string, AutomationPreflightResult>;
  isLoading: boolean;
  error: ApiError | null;
  selectedAutomation: Automation | null;
  installState: Record<string, { isLoading: boolean; error: ApiError | null; steps?: InstallAutomationResult['steps'] }>;
}

export interface UseAutomationsActions {
  loadAutomations: () => Promise<void>;
  discoverAutomations: () => Promise<void>;
  selectAutomation: (automation: Automation | null) => void;
  installAutomation: (automationId: string) => Promise<InstallAutomationResult | null>;
  enableAutomation: (automationId: string) => Promise<void>;
  disableAutomation: (automationId: string) => Promise<void>;
  uninstallAutomation: (automationId: string) => Promise<void>;
  runAutomation: (automationId: string, profileId?: string | null) => Promise<RunAutomationResult | null>;
  refreshAutomation: (automationId: string) => Promise<void>;
  checkForUpdates: () => Promise<void>;
  clearError: () => void;
}

export type UseAutomationsReturn = UseAutomationsState & UseAutomationsActions;

function applyPreflightStatuses(
  items: Automation[],
  preflightById: Record<string, AutomationPreflightResult>,
): Automation[] {
  return items.map((automation) => {
    const preflight = preflightById[automation.id];
    const mutableReadinessStates = ['discovered', 'ready', 'disabled', 'blocked', 'error'];
    if (!preflight || !mutableReadinessStates.includes(automation.status)) {
      return automation;
    }
    if (preflight.status === 'ready' && ['discovered', 'blocked', 'error'].includes(automation.status)) {
      return { ...automation, status: 'ready' as const };
    }
    if (preflight.status === 'blocked') {
      return { ...automation, status: 'blocked' as const };
    }
    return automation;
  });
}

export function useAutomations(): UseAutomationsReturn {
  const [automations, setAutomations] = useState<Automation[]>([]);
  const [preflightById, setPreflightById] = useState<Record<string, AutomationPreflightResult>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [selectedAutomation, setSelectedAutomation] = useState<Automation | null>(null);
  const [installState, setInstallState] = useState<Record<string, { isLoading: boolean; error: ApiError | null; steps?: InstallAutomationResult['steps'] }>>({});

  const clearError = useCallback(() => setError(null), []);

  const loadAutomations = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      // The global preflight discovers manifests before we read the persisted
      // list, so the first page load has no manual-discovery race.
      const preflight = await automationsApi.preflightAllAutomations();
      const response = await automationsApi.listAutomations();
      const nextPreflightById = Object.fromEntries(
        preflight.automations.map((item) => [item.automation_id, item]),
      );
      setPreflightById(nextPreflightById);
      setAutomations(applyPreflightStatuses(response.automations, nextPreflightById));
    } catch (err) {
      setError(err instanceof ApiError ? err : ApiError.networkError(String(err)));
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Kept for compatibility with the existing UI, but discovery/preflight now
  // happen together and never require a separate manual discovery step.
  const discoverAutomations = useCallback(async () => loadAutomations(), [loadAutomations]);

  const selectAutomation = useCallback((automation: Automation | null) => {
    setSelectedAutomation(automation);
  }, []);

  const installAutomation = useCallback(async (automationId: string): Promise<InstallAutomationResult | null> => {
    setInstallState((previous) => ({
      ...previous,
      [automationId]: { isLoading: true, error: null, steps: [] },
    }));
    try {
      const result = await automationsApi.installAutomation(automationId);
      setInstallState((previous) => ({
        ...previous,
        [automationId]: { isLoading: false, error: null, steps: result.steps },
      }));
      await loadAutomations();
      return result;
    } catch (err) {
      const apiError = err instanceof ApiError ? err : ApiError.networkError(String(err));
      setInstallState((previous) => ({
        ...previous,
        [automationId]: { isLoading: false, error: apiError },
      }));
      await loadAutomations();
      return null;
    }
  }, [loadAutomations]);

  const enableAutomation = useCallback(async (automationId: string) => {
    setError(null);
    try {
      await automationsApi.enableAutomation(automationId);
      await loadAutomations();
    } catch (err) {
      const apiError = err instanceof ApiError ? err : ApiError.networkError(String(err));
      setError(apiError);
      throw apiError;
    }
  }, [loadAutomations]);

  const disableAutomation = useCallback(async (automationId: string) => {
    setError(null);
    try {
      await automationsApi.disableAutomation(automationId);
      await loadAutomations();
    } catch (err) {
      const apiError = err instanceof ApiError ? err : ApiError.networkError(String(err));
      setError(apiError);
      throw apiError;
    }
  }, [loadAutomations]);

  const uninstallAutomation = useCallback(async (automationId: string) => {
    setError(null);
    try {
      await automationsApi.uninstallAutomation(automationId);
      await loadAutomations();
    } catch (err) {
      const apiError = err instanceof ApiError ? err : ApiError.networkError(String(err));
      setError(apiError);
      throw apiError;
    }
  }, [loadAutomations]);

  const runAutomation = useCallback(async (
    automationId: string,
    profileId?: string | null,
  ): Promise<RunAutomationResult | null> => {
    setError(null);
    try {
      const result = await automationsApi.runAutomation(automationId, profileId);
      return result;
    } catch (err) {
      const apiError = err instanceof ApiError ? err : ApiError.networkError(String(err));
      setError(apiError);
      return null;
    }
  }, []);

  const refreshAutomation = useCallback(async (automationId: string) => {
    setError(null);
    try {
      const [automation, preflight] = await Promise.all([
        automationsApi.getAutomation(automationId),
        automationsApi.preflightAutomation(automationId),
      ]);
      setPreflightById((previous) => ({ ...previous, [automationId]: preflight }));
      const hydrated = applyPreflightStatuses([automation], { [automationId]: preflight })[0];
      setAutomations((previous) => previous.map((item) => item.id === automationId ? hydrated : item));
      if (selectedAutomation?.id === automationId) {
        setSelectedAutomation(hydrated);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err : ApiError.networkError(String(err)));
    }
  }, [selectedAutomation]);

  const checkForUpdates = useCallback(async () => {
    setError(null);
    try {
      await automationsApi.checkForUpdates();
      await loadAutomations();
    } catch (err) {
      setError(err instanceof ApiError ? err : ApiError.networkError(String(err)));
    }
  }, [loadAutomations]);

  useEffect(() => {
    void loadAutomations();
  }, [loadAutomations]);

  return {
    automations,
    preflightById,
    isLoading,
    error,
    selectedAutomation,
    installState,
    loadAutomations,
    discoverAutomations,
    selectAutomation,
    installAutomation,
    enableAutomation,
    disableAutomation,
    uninstallAutomation,
    runAutomation,
    refreshAutomation,
    checkForUpdates,
    clearError,
  };
}
