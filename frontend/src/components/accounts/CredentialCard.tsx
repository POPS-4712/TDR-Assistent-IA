import { STATUS_COLORS, STATUS_LABELS } from '../../types';
import type { Credential, Provider } from '../../types';

interface CredentialCardProps {
  credential: Credential;
  provider?: Provider;
  onRefresh: (id: string) => void;
  onValidate: (id: string) => void;
  onRevoke: (id: string) => void;
  isRefreshing?: boolean;
}

const ICONS: Record<string, string> = {
  google: '🔍', openai: '🤖', gemini: '💎', anthropic: '🧠',
  openrouter: '🔀', telegram: '📱', whatsapp_cloud: '💬', header_auth: '🔐',
};

const formatDate = (value?: string) => value ? new Date(value).toLocaleDateString() : 'Sin comprobar';

export function CredentialCard({ credential, provider, onRefresh, onValidate, onRevoke, isRefreshing }: CredentialCardProps) {
  const statusColor = STATUS_COLORS[credential.status] || STATUS_COLORS.unknown;
  const statusLabel = STATUS_LABELS[credential.status] || credential.status;
  const needsReconnect = credential.status === 'expired' || credential.status === 'reauth_required';
  const publicDetails = Object.entries(credential.metadata || {})
    .filter(([, value]) => typeof value === 'string' || typeof value === 'number')
    .map(([key, value]) => `${key.replace(/_/g, ' ')}: ${value}`);

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-gray-100 text-xl">{ICONS[credential.provider] || '🔐'}</div>
          <div className="min-w-0">
            <h3 className="truncate font-medium text-gray-900">{provider?.display_name || credential.provider}</h3>
            <p className="truncate text-sm text-gray-500">{credential.account_identifier}</p>
          </div>
        </div>
        <span className={`shrink-0 rounded-full px-3 py-1 text-sm font-medium ${statusColor}`}>{statusLabel}</span>
      </div>
      <div className="mt-3 space-y-1 text-xs text-gray-500">
        {credential.scopes.length > 0 && <p className="break-words">Scopes: {credential.scopes.join(', ')}</p>}
        <p>Última validación: {formatDate(credential.last_validation)}</p>
        {credential.expires_at && <p className={needsReconnect ? 'text-red-600' : ''}>Vence: {formatDate(credential.expires_at)}</p>}
        {publicDetails.map((detail) => <p key={detail} className="break-words">{detail}</p>)}
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <button onClick={() => onValidate(credential.id)} disabled={isRefreshing || credential.status === 'revoked'} className="rounded-lg border border-blue-200 px-3 py-1.5 text-sm text-blue-700 hover:bg-blue-50 disabled:opacity-50">Validar</button>
        <button onClick={() => onRefresh(credential.id)} disabled={isRefreshing || credential.status === 'revoked' || credential.status === 'disconnected'} className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50">{isRefreshing ? 'Actualizando…' : needsReconnect ? 'Reconectar' : 'Actualizar'}</button>
        <button onClick={() => onRevoke(credential.id)} disabled={credential.status === 'revoked' || credential.status === 'disconnected'} className="rounded-lg bg-red-100 px-3 py-1.5 text-sm text-red-700 hover:bg-red-200 disabled:opacity-50">Desconectar</button>
      </div>
    </div>
  );
}
