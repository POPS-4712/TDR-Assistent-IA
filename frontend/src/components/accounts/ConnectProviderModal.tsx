import { useEffect, useState } from 'react';
import type { Provider, StructuredCredentialRequest } from '../../types';

interface ConnectProviderModalProps {
  isOpen: boolean;
  provider: Provider | null;
  onClose: () => void;
  onConnectOAuth: (provider: string, scopes?: string[]) => Promise<void>;
  onStoreApiKey: (provider: string, accountIdentifier: string, apiKey: string) => Promise<void>;
  onStoreToken: (provider: string, accountIdentifier: string, token: string) => Promise<void>;
  onStoreStructuredCredential: (request: StructuredCredentialRequest) => Promise<void>;
  isLoading: boolean;
}

export function ConnectProviderModal({
  isOpen,
  provider,
  onClose,
  onConnectOAuth,
  onStoreApiKey,
  onStoreToken,
  onStoreStructuredCredential,
  isLoading,
}: ConnectProviderModalProps) {
  const [accountIdentifier, setAccountIdentifier] = useState('');
  const [secret, setSecret] = useState('');
  const [phoneNumberId, setPhoneNumberId] = useState('');
  const [wabaId, setWabaId] = useState('');
  const [apiVersion, setApiVersion] = useState('');
  const [headerName, setHeaderName] = useState('Authorization');
  const [validationUrl, setValidationUrl] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setAccountIdentifier('');
      setSecret('');
      setPhoneNumberId('');
      setWabaId('');
      setApiVersion('');
      setHeaderName('Authorization');
      setValidationUrl('');
      setError(null);
    }
  }, [isOpen]);

  if (!isOpen || !provider) return null;

  const structured = provider.credential_type === 'structured';
  const isWhatsApp = provider.name === 'whatsapp_cloud';
  const isHeaderAuth = provider.name === 'header_auth';

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    try {
      if (provider.credential_type === 'oauth') {
        await onConnectOAuth(provider.name, provider.scopes);
      } else if (provider.credential_type === 'api_key') {
        if (!accountIdentifier.trim() || !secret.trim()) throw new Error('Completa la cuenta y la clave API.');
        await onStoreApiKey(provider.name, accountIdentifier.trim(), secret.trim());
      } else if (provider.credential_type === 'token') {
        if (!accountIdentifier.trim() || !secret.trim()) throw new Error('Completa la cuenta y el token.');
        await onStoreToken(provider.name, accountIdentifier.trim(), secret.trim());
      } else if (structured && isWhatsApp) {
        if (!accountIdentifier.trim() || !secret.trim() || !phoneNumberId.trim() || !apiVersion.trim()) {
          throw new Error('Completa la cuenta, token, Phone Number ID y versión de Graph API.');
        }
        await onStoreStructuredCredential({
          provider: provider.name,
          account_identifier: accountIdentifier.trim(),
          secrets: { access_token: secret.trim() },
          metadata: {
            phone_number_id: phoneNumberId.trim(),
            waba_id: wabaId.trim(),
            api_version: apiVersion.trim(),
          },
        });
      } else if (structured && isHeaderAuth) {
        if (!accountIdentifier.trim() || !secret.trim() || !headerName.trim()) {
          throw new Error('Completa la cuenta, el nombre del header y su valor.');
        }
        await onStoreStructuredCredential({
          provider: provider.name,
          account_identifier: accountIdentifier.trim(),
          secrets: { header_value: secret.trim() },
          metadata: { header_name: headerName.trim(), validation_url: validationUrl.trim() },
        });
      } else {
        throw new Error('Este tipo de cuenta aún no admite conexión desde la interfaz.');
      }
      onClose();
    } catch (submissionError) {
      setError(submissionError instanceof Error ? submissionError.message : 'No se pudo conectar la cuenta.');
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto" role="dialog" aria-modal="true">
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="fixed inset-0 bg-black/50" onClick={onClose} aria-hidden="true" />
        <div className="relative w-full max-w-md rounded-lg bg-white shadow-xl">
          <div className="flex items-center justify-between border-b border-gray-200 p-4">
            <h2 className="text-lg font-semibold text-gray-900">Conectar {provider.display_name}</h2>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600" aria-label="Cerrar">×</button>
          </div>
          <form onSubmit={handleSubmit} className="space-y-4 p-4">
            {provider.description && <p className="text-sm text-gray-600">{provider.description}</p>}
            {provider.credential_type === 'oauth' ? (
              <div className="space-y-3 text-sm text-gray-600">
                <p>Se abrirá la autorización segura de {provider.display_name}.</p>
                {!!provider.scopes?.length && <p className="text-xs">Scopes solicitados: {provider.scopes.join(', ')}</p>}
              </div>
            ) : (
              <>
                <label className="block text-sm font-medium text-gray-700">Identificador de cuenta
                  <input value={accountIdentifier} onChange={(e) => setAccountIdentifier(e.target.value)} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2" placeholder="Cuenta o etiqueta local" required />
                </label>
                {isWhatsApp && <>
                  <label className="block text-sm font-medium text-gray-700">Phone Number ID
                    <input value={phoneNumberId} onChange={(e) => setPhoneNumberId(e.target.value)} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2" inputMode="numeric" required />
                  </label>
                  <label className="block text-sm font-medium text-gray-700">WABA ID <span className="font-normal text-gray-500">(opcional)</span>
                    <input value={wabaId} onChange={(e) => setWabaId(e.target.value)} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2" inputMode="numeric" />
                  </label>
                  <label className="block text-sm font-medium text-gray-700">Versión de Graph API
                    <input value={apiVersion} onChange={(e) => setApiVersion(e.target.value)} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2" placeholder="v26.0" required />
                  </label>
                </>}
                {isHeaderAuth && <>
                  <label className="block text-sm font-medium text-gray-700">Nombre del header
                    <input value={headerName} onChange={(e) => setHeaderName(e.target.value)} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2" required />
                  </label>
                  <label className="block text-sm font-medium text-gray-700">URL de validación <span className="font-normal text-gray-500">(HTTPS opcional)</span>
                    <input value={validationUrl} onChange={(e) => setValidationUrl(e.target.value)} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2" type="url" placeholder="https://api.example.com/me" />
                  </label>
                </>}
                <label className="block text-sm font-medium text-gray-700">{provider.credential_type === 'api_key' ? 'Clave API' : isHeaderAuth ? 'Valor del header' : 'Token de acceso'}
                  <input type="password" value={secret} onChange={(e) => setSecret(e.target.value)} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2" autoComplete="off" required />
                  <span className="mt-1 block text-xs font-normal text-gray-500">Este valor se envía al almacenamiento seguro y nunca se muestra de nuevo.</span>
                </label>
              </>
            )}
            {error && <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
            <div className="flex gap-3 pt-2">
              <button type="button" onClick={onClose} className="flex-1 rounded-lg bg-gray-100 px-4 py-2 text-sm font-medium text-gray-700">Cancelar</button>
              <button type="submit" disabled={isLoading} className="flex-1 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
                {isLoading ? 'Conectando…' : provider.credential_type === 'oauth' ? 'Autorizar' : 'Conectar'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
