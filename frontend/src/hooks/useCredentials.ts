/**
 * Hook for managing credentials state and operations.
 * All reloaded account records contain public metadata only.
 */

import { useState, useCallback, useEffect } from 'react';
import { ApiError } from '../api/client';
import * as credentialsApi from '../api/credentials';
import { preflightAllAutomations } from '../api/automations';
import type {
  Credential,
  Provider,
  ConnectCredentialResponse,
  StoreCredentialResponse,
  StructuredCredentialRequest,
  CredentialValidationResponse,
} from '../types';

export interface UseCredentialsState {
  credentials: Credential[];
  providers: Provider[];
  isLoading: boolean;
  error: ApiError | null;
  selectedCredential: Credential | null;
  connectState: Record<string, { isLoading: boolean; error: ApiError | null; authUrl?: string }>;
}

export interface UseCredentialsActions {
  loadCredentials: () => Promise<void>;
  loadProviders: () => Promise<void>;
  selectCredential: (credential: Credential | null) => void;
  connectOAuth: (provider: string, scopes?: string[]) => Promise<ConnectCredentialResponse | null>;
  storeApiKey: (provider: string, accountIdentifier: string, apiKey: string) => Promise<StoreCredentialResponse | null>;
  storeToken: (provider: string, accountIdentifier: string, token: string) => Promise<StoreCredentialResponse | null>;
  storeStructuredCredential: (request: StructuredCredentialRequest) => Promise<StoreCredentialResponse | null>;
  validateCredential: (credentialId: string) => Promise<CredentialValidationResponse | null>;
  refreshCredential: (credentialId: string) => Promise<void>;
  revokeCredential: (credentialId: string) => Promise<void>;
  clearError: () => void;
}

export type UseCredentialsReturn = UseCredentialsState & UseCredentialsActions;

export function useCredentials(): UseCredentialsReturn {
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [selectedCredential, setSelectedCredential] = useState<Credential | null>(null);
  const [connectState, setConnectState] = useState<Record<string, { isLoading: boolean; error: ApiError | null; authUrl?: string }>>({});

  const clearError = useCallback(() => setError(null), []);

  const revalidateAutomations = useCallback(async () => {
    try {
      await preflightAllAutomations();
    } catch {
      // Account updates stay usable even if a separate read-only preflight is temporarily unavailable.
    }
  }, []);

  const loadCredentials = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await credentialsApi.listCredentials();
      setCredentials(response.credentials);
    } catch (err) {
      setError(err instanceof ApiError ? err : ApiError.networkError(String(err)));
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadProviders = useCallback(async () => {
    setError(null);
    try {
      const response = await credentialsApi.listProviders();
      setProviders(response.providers);
    } catch (err) {
      setError(err instanceof ApiError ? err : ApiError.networkError(String(err)));
    }
  }, []);

  const selectCredential = useCallback((credential: Credential | null) => {
    setSelectedCredential(credential);
  }, []);

  const connectOAuth = useCallback(async (provider: string, scopes?: string[]) => {
    setConnectState((previous) => ({ ...previous, [provider]: { isLoading: true, error: null } }));
    try {
      const result = await credentialsApi.connectCredential({ provider, scopes });
      setConnectState((previous) => ({
        ...previous,
        [provider]: { isLoading: false, error: null, authUrl: result.auth_url },
      }));
      if (result.auth_url) window.open(result.auth_url, '_blank', 'width=600,height=700');
      return result;
    } catch (err) {
      const apiError = err instanceof ApiError ? err : ApiError.networkError(String(err));
      setConnectState((previous) => ({ ...previous, [provider]: { isLoading: false, error: apiError } }));
      return null;
    }
  }, []);

  const storeApiKey = useCallback(async (provider: string, accountIdentifier: string, apiKey: string) => {
    setError(null);
    try {
      const result = await credentialsApi.storeApiKey({ provider, account_identifier: accountIdentifier, api_key: apiKey });
      await Promise.all([loadCredentials(), revalidateAutomations()]);
      return result;
    } catch (err) {
      setError(err instanceof ApiError ? err : ApiError.networkError(String(err)));
      return null;
    }
  }, [loadCredentials, revalidateAutomations]);

  const storeToken = useCallback(async (provider: string, accountIdentifier: string, token: string) => {
    setError(null);
    try {
      const result = await credentialsApi.storeToken({ provider, account_identifier: accountIdentifier, token });
      await Promise.all([loadCredentials(), revalidateAutomations()]);
      return result;
    } catch (err) {
      setError(err instanceof ApiError ? err : ApiError.networkError(String(err)));
      return null;
    }
  }, [loadCredentials, revalidateAutomations]);

  const storeStructuredCredential = useCallback(async (request: StructuredCredentialRequest) => {
    setError(null);
    try {
      const result = await credentialsApi.storeStructuredCredential(request);
      await Promise.all([loadCredentials(), revalidateAutomations()]);
      return result;
    } catch (err) {
      setError(err instanceof ApiError ? err : ApiError.networkError(String(err)));
      return null;
    }
  }, [loadCredentials, revalidateAutomations]);

  const validateCredential = useCallback(async (credentialId: string) => {
    setError(null);
    try {
      const result = await credentialsApi.validateCredential(credentialId);
      await Promise.all([loadCredentials(), revalidateAutomations()]);
      return result;
    } catch (err) {
      setError(err instanceof ApiError ? err : ApiError.networkError(String(err)));
      return null;
    }
  }, [loadCredentials, revalidateAutomations]);

  const refreshCredential = useCallback(async (credentialId: string) => {
    setError(null);
    try {
      await credentialsApi.refreshCredential(credentialId);
      await Promise.all([loadCredentials(), revalidateAutomations()]);
    } catch (err) {
      const apiError = err instanceof ApiError ? err : ApiError.networkError(String(err));
      setError(apiError);
      throw apiError;
    }
  }, [loadCredentials, revalidateAutomations]);

  const revokeCredential = useCallback(async (credentialId: string) => {
    setError(null);
    try {
      await credentialsApi.revokeCredential(credentialId);
      await Promise.all([loadCredentials(), revalidateAutomations()]);
    } catch (err) {
      const apiError = err instanceof ApiError ? err : ApiError.networkError(String(err));
      setError(apiError);
      throw apiError;
    }
  }, [loadCredentials, revalidateAutomations]);

  useEffect(() => {
    void loadCredentials();
    void loadProviders();
  }, [loadCredentials, loadProviders]);

  return {
    credentials,
    providers,
    isLoading,
    error,
    selectedCredential,
    connectState,
    loadCredentials,
    loadProviders,
    selectCredential,
    connectOAuth,
    storeApiKey,
    storeToken,
    storeStructuredCredential,
    validateCredential,
    refreshCredential,
    revokeCredential,
    clearError,
  };
}
