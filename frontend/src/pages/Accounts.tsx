/**
 * Accounts page for Automation Center
 */

import { useEffect, useState } from 'react';
import { useCredentials } from '../hooks/useCredentials';
import { CredentialCard } from '../components/accounts/CredentialCard';
import { ConnectProviderModal } from '../components/accounts/ConnectProviderModal';
import type { Provider, StructuredCredentialRequest } from '../types';

const PROVIDER_ORDER = ['google', 'gemini', 'whatsapp_cloud', 'header_auth', 'telegram', 'openai', 'anthropic', 'openrouter'];

export function Accounts() {
  const { 
    credentials, 
    providers, 
    isLoading, 
    error, 
    loadCredentials, 
    loadProviders,
    connectOAuth,
    storeApiKey,
    storeToken,
    storeStructuredCredential,
    validateCredential,
    refreshCredential,
    revokeCredential,
    clearError,
  } = useCredentials();

  const [selectedProvider, setSelectedProvider] = useState<Provider | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [refreshingIds, setRefreshingIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    loadCredentials();
    loadProviders();
  }, [loadCredentials, loadProviders]);

  const handleConnect = (provider: Provider) => {
    setSelectedProvider(provider);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedProvider(null);
  };

  const handleConnectOAuth = async (providerName: string, scopes?: string[]) => {
    setIsConnecting(true);
    try {
      await connectOAuth(providerName, scopes);
    } finally {
      setIsConnecting(false);
    }
  };

  const handleStoreApiKey = async (providerName: string, accountIdentifier: string, apiKey: string) => {
    setIsConnecting(true);
    try {
      await storeApiKey(providerName, accountIdentifier, apiKey);
    } finally {
      setIsConnecting(false);
    }
  };

  const handleStoreToken = async (providerName: string, accountIdentifier: string, token: string) => {
    setIsConnecting(true);
    try {
      await storeToken(providerName, accountIdentifier, token);
    } finally {
      setIsConnecting(false);
    }
  };

  const handleStoreStructuredCredential = async (request: StructuredCredentialRequest) => {
    setIsConnecting(true);
    try {
      await storeStructuredCredential(request);
    } finally {
      setIsConnecting(false);
    }
  };

  const handleValidate = async (id: string) => {
    setRefreshingIds(prev => new Set(prev).add(id));
    try {
      await validateCredential(id);
    } finally {
      setRefreshingIds(prev => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  };

  const handleRefresh = async (id: string) => {
    setRefreshingIds(prev => new Set(prev).add(id));
    try {
      await refreshCredential(id);
    } finally {
      setRefreshingIds(prev => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  };

  const handleRevoke = async (id: string) => {
    if (window.confirm('Revoking this account may disable automations that depend on it. Are you sure?')) {
      try {
        await revokeCredential(id);
      } catch (err) {
        // Error handled in hook
      }
    }
  };

  // Sort providers by predefined order
  const sortedProviders = [...providers].sort((a, b) => {
    const aIndex = PROVIDER_ORDER.indexOf(a.name.toLowerCase());
    const bIndex = PROVIDER_ORDER.indexOf(b.name.toLowerCase());
    return (aIndex === -1 ? 999 : aIndex) - (bIndex === -1 ? 999 : bIndex);
  });

  // Group credentials by provider
  const credentialsByProvider = credentials.reduce((acc, cred) => {
    if (!acc[cred.provider]) acc[cred.provider] = [];
    acc[cred.provider].push(cred);
    return acc;
  }, {} as Record<string, typeof credentials>);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Accounts</h1>
        <p className="text-gray-500 mt-1">Manage your connected accounts and credentials</p>
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

      {/* Providers Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="bg-white rounded-lg border border-gray-200 p-5 animate-pulse">
              <div className="flex items-center space-x-3">
                <div className="w-12 h-12 bg-gray-200 rounded-lg" />
                <div className="space-y-2">
                  <div className="h-4 bg-gray-200 rounded w-3/4" />
                  <div className="h-3 bg-gray-200 rounded w-1/2" />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {sortedProviders.map((provider) => {
            const providerCredentials = credentialsByProvider[provider.name] || [];
            const primaryCredential = providerCredentials[0];
            const isRefreshing = primaryCredential ? refreshingIds.has(primaryCredential.id) : false;

            return (
              <div key={provider.name} className="bg-white rounded-lg border border-gray-200 p-5">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center text-xl">
                      {provider.name === 'google' && '🔍'}
                      {provider.name === 'openai' && '🤖'}
                      {provider.name === 'gemini' && '💎'}
                      {provider.name === 'anthropic' && '🧠'}
                      {provider.name === 'openrouter' && '🔀'}
                      {provider.name === 'telegram' && '📱'}
                      {provider.name === 'whatsapp_cloud' && '💬'}
                      {provider.name === 'header_auth' && '🔐'}
                    </div>
                    <div>
                      <h3 className="font-medium text-gray-900">{provider.display_name}</h3>
                      <p className="text-sm text-gray-500 capitalize">{provider.credential_type}</p>
                    </div>
                  </div>
                </div>

                {primaryCredential ? (
                  <CredentialCard
                    credential={primaryCredential}
                    provider={provider}
                    onRefresh={handleRefresh}
                    onValidate={handleValidate}
                    onRevoke={handleRevoke}
                    isRefreshing={isRefreshing}
                  />
                ) : (
                  <button
                    onClick={() => handleConnect(provider)}
                    disabled={isConnecting}
                    className="w-full px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                  >
                    Connect {provider.display_name}
                  </button>
                )}

                {providerCredentials.length > 1 && (
                  <div className="mt-3 pt-3 border-t border-gray-100">
                    <p className="text-xs text-gray-500">
                      +{providerCredentials.length - 1} more account(s)
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Connect Provider Modal */}
      <ConnectProviderModal
        isOpen={isModalOpen}
        provider={selectedProvider}
        onClose={handleCloseModal}
        onConnectOAuth={handleConnectOAuth}
        onStoreApiKey={handleStoreApiKey}
        onStoreToken={handleStoreToken}
        onStoreStructuredCredential={handleStoreStructuredCredential}
        isLoading={isConnecting}
      />
    </div>
  );
}