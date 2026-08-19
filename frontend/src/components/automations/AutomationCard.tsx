/**
 * Automation card with safe preflight and lifecycle actions.
 */

import { STATUS_COLORS, STATUS_LABELS } from '../../types';
import type { Automation, AutomationPreflightResult } from '../../types';

interface AutomationCardProps {
  automation: Automation;
  preflight?: AutomationPreflightResult;
  installState?: { isLoading: boolean; error: unknown; steps?: Array<{ step: number; name: string; status: string; message?: string }> };
  onInstall: (id: string) => void;
  onEnable: (id: string) => void;
  onDisable: (id: string) => void;
  onRun: (id: string) => void;
  onUninstall: (id: string) => void;
  onRetry: (id: string) => void;
}

export function AutomationCard({
  automation,
  preflight,
  installState,
  onInstall,
  onEnable,
  onDisable,
  onRun,
  onUninstall,
  onRetry,
}: AutomationCardProps) {
  const statusColor = STATUS_COLORS[automation.status] || STATUS_COLORS.unknown;
  const statusLabel = STATUS_LABELS[automation.status] || automation.status;
  const isInstalling = installState?.isLoading || automation.status === 'installing';
  const installError = installState?.error;
  const installSteps = installState?.steps;
  const missingRequirements = preflight?.missing_requirements || [];
  const accounts = preflight?.accounts || [];
  const isReady = preflight?.status === 'ready';

  const renderActions = () => {
    if (isInstalling) {
      return (
        <div className="space-y-2" aria-live="polite">
          <div className="text-sm text-gray-600">Installing safely…</div>
          {installSteps && installSteps.length > 0 && (
            <div className="space-y-1">
              {installSteps.map((step) => (
                <div key={step.step} className="flex items-center space-x-2 text-xs">
                  <div className={`w-1.5 h-1.5 rounded-full ${
                    step.status === 'completed' ? 'bg-green-500' :
                    step.status === 'running' ? 'bg-blue-500 animate-pulse' :
                    step.status === 'failed' ? 'bg-red-500' : 'bg-gray-300'
                  }`} />
                  <span className={step.status === 'failed' ? 'text-red-600' : 'text-gray-600'}>
                    {step.name}{step.message ? ` — ${step.message}` : ''}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      );
    }

    if (installError) {
      return (
        <div className="space-y-2">
          <div className="text-sm text-red-600">Installation failed safely.</div>
          <button onClick={() => onRetry(automation.id)} className="w-full px-3 py-1.5 text-sm bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors">
            Recheck and retry
          </button>
        </div>
      );
    }

    if (automation.status === 'blocked' || (!isReady && automation.status === 'discovered')) {
      return (
        <div className="space-y-2">
          <div className="rounded-lg bg-yellow-50 px-3 py-2 text-xs text-yellow-800">
            Installation is disabled until every required account, scope, mapping and runtime check passes. Verification runs automatically.
          </div>
          <a href="/accounts" className="block w-full px-3 py-1.5 text-center text-sm bg-yellow-100 text-yellow-800 rounded-lg hover:bg-yellow-200 transition-colors">
            Connect accounts
          </a>
        </div>
      );
    }

    switch (automation.status) {
      case 'discovered':
      case 'ready':
        return <button onClick={() => onInstall(automation.id)} className="w-full px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">Install</button>;
      case 'installed':
        return (
          <div className="space-y-2">
            <button onClick={() => onEnable(automation.id)} className="w-full px-3 py-1.5 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors">Enable</button>
            <button onClick={() => onUninstall(automation.id)} className="w-full px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors">Uninstall</button>
          </div>
        );
      case 'enabled':
        return (
          <div className="space-y-2">
            <button onClick={() => onRun(automation.id)} className="w-full px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors">Run</button>
            <button onClick={() => onDisable(automation.id)} className="w-full px-3 py-1.5 text-sm bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition-colors">Disable</button>
          </div>
        );
      case 'disabled':
        return (
          <div className="space-y-2">
            <button onClick={() => onEnable(automation.id)} className="w-full px-3 py-1.5 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors">Enable</button>
            <button onClick={() => onUninstall(automation.id)} className="w-full px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors">Uninstall</button>
          </div>
        );
      case 'error':
        return <button onClick={() => onRetry(automation.id)} className="w-full px-3 py-1.5 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors">Recheck and retry</button>;
      default:
        return null;
    }
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-lg font-medium text-gray-900">{automation.name}</h3>
          <p className="text-sm text-gray-500 mt-1">{automation.description}</p>
          <div className="flex items-center space-x-3 mt-2 text-xs text-gray-500">
            <span>v{automation.version}</span>
            <span className="capitalize">{automation.category || 'general'}</span>
            <span>Profile: optional at run time</span>
          </div>
        </div>
        <span className={`shrink-0 px-3 py-1 text-sm font-medium rounded-full ${statusColor}`}>{statusLabel}</span>
      </div>

      {(automation.dependencies.length > 0 || accounts.length > 0 || missingRequirements.length > 0) && (
        <div className="mt-4 pt-4 border-t border-gray-100 space-y-3">
          {automation.dependencies.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-500 mb-2">Runtime requirements</p>
              <div className="flex flex-wrap gap-2">
                {automation.dependencies.map((dependency) => <span key={dependency} className="px-2 py-0.5 text-xs bg-gray-100 text-gray-700 rounded">{dependency}</span>)}
              </div>
            </div>
          )}

          {accounts.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-500 mb-2">Connected accounts</p>
              <div className="space-y-1">
                {accounts.map((account) => (
                  <div key={account.provider} className="flex items-center justify-between text-xs">
                    <span className="text-gray-700">{account.provider}{account.account ? ` · ${account.account}` : ''}</span>
                    <span className={account.compatible ? 'text-green-700' : 'text-yellow-700'}>{account.compatible ? 'compatible' : account.status}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {missingRequirements.length > 0 && (
            <div className="rounded-lg bg-yellow-50 p-3">
              <p className="text-xs font-medium text-yellow-900 mb-1">Blocked because</p>
              <ul className="space-y-1 text-xs text-yellow-800">
                {missingRequirements.map((reason) => <li key={reason}>• {reason}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}

      <div className="mt-4">{renderActions()}</div>
    </div>
  );
}
