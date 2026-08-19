/**
 * Credentials API endpoints
 */

import { api } from './client';
import type {
  Credential,
  CredentialListResponse,
  ProvidersResponse,
  ConnectCredentialRequest,
  ConnectCredentialResponse,
  ApiKeyRequest,
  TokenRequest,
  StoreCredentialResponse,
  RefreshCredentialResponse,
  RevokeCredentialResponse,
  OAuthCallbackResponse,
  StructuredCredentialRequest,
  CredentialValidationResponse,
} from '../types';

export async function listCredentials(): Promise<CredentialListResponse> {
  const response = await api.get<CredentialListResponse>('/credentials');
  return response.data;
}

export async function listProviders(): Promise<ProvidersResponse> {
  const response = await api.get<ProvidersResponse>('/credentials/providers');
  return response.data;
}

export async function getCredential(credentialId: string): Promise<Credential> {
  const response = await api.get<Credential>(`/credentials/${credentialId}`);
  return response.data;
}

export async function connectCredential(
  request: ConnectCredentialRequest
): Promise<ConnectCredentialResponse> {
  const response = await api.post<ConnectCredentialResponse>('/credentials/connect', request);
  return response.data;
}

export async function storeApiKey(request: ApiKeyRequest): Promise<StoreCredentialResponse> {
  const response = await api.post<StoreCredentialResponse>('/credentials/api-key', request);
  return response.data;
}

export async function storeToken(request: TokenRequest): Promise<StoreCredentialResponse> {
  const response = await api.post<StoreCredentialResponse>('/credentials/token', request);
  return response.data;
}

export async function storeStructuredCredential(
  request: StructuredCredentialRequest
): Promise<StoreCredentialResponse> {
  const response = await api.post<StoreCredentialResponse>('/credentials/structured', request);
  return response.data;
}

export async function validateCredential(
  credentialId: string
): Promise<CredentialValidationResponse> {
  const response = await api.post<CredentialValidationResponse>(
    `/credentials/${credentialId}/validate`,
    {}
  );
  return response.data;
}

export async function generateOAuthUrl(
  provider: string,
  scopes?: string[]
): Promise<{ auth_url: string; state: string }> {
  const params = scopes ? { scopes: scopes.join(',') } : undefined;
  const response = await api.get<{ auth_url: string; state: string }>(
    `/credentials/${provider}/authorize`,
    { params }
  );
  return response.data;
}

export async function handleOAuthCallback(
  provider: string,
  code: string,
  state: string,
  error?: string
): Promise<OAuthCallbackResponse> {
  const params = new URLSearchParams({ code, state });
  if (error) params.append('error', error);
  
  const response = await api.get<OAuthCallbackResponse>(
    `/credentials/${provider}/callback?${params.toString()}`
  );
  return response.data;
}

export async function refreshCredential(credentialId: string): Promise<RefreshCredentialResponse> {
  const response = await api.post<RefreshCredentialResponse>(`/credentials/${credentialId}/refresh`, {});
  return response.data;
}

export async function revokeCredential(credentialId: string): Promise<RevokeCredentialResponse> {
  const response = await api.delete<RevokeCredentialResponse>(`/credentials/${credentialId}`);
  return response.data;
}