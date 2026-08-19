import { useState } from 'react';
import { useSystem } from '../hooks/useSystem';
import { STATUS_COLORS, STATUS_LABELS } from '../types';

const SERVICE_LABELS: Record<string, string> = {
  backend: 'Backend',
  postgres: 'PostgreSQL',
  n8n: 'n8n',
  playwright: 'Playwright',
  frontend: 'Desktop UI',
};

function formatBytes(bytes?: number): string {
  if (bytes === undefined) return 'Checking';
  return `${Math.floor(bytes / 1_000_000_000)} GB`;
}

export function System() {
  const {
    systemStatus,
    systemConfig,
    setupStatus,
    diagnostics,
    isLoading,
    error,
    checkHealth,
    controlService,
    refreshAll,
    clearError,
  } = useSystem();
  const [advancedMode, setAdvancedMode] = useState(false);
  const [healthSummary, setHealthSummary] = useState<boolean | null>(null);

  const services = systemStatus?.services || {};
  const controlAvailable = diagnostics?.local_service_control.available === true;

  const handleHealthCheck = async () => {
    const result = await checkHealth();
    setHealthSummary(result.healthy);
    await refreshAll();
  };

  const handleControl = async (service: 'backend' | 'postgres' | 'n8n' | 'playwright' | 'frontend', action: 'start' | 'stop' | 'restart') => {
    const requiresConfirmation = action !== 'start';
    if (requiresConfirmation && !window.confirm(`${action === 'stop' ? 'Stop' : 'Restart'} ${SERVICE_LABELS[service]}? This affects only Automation Center local services.`)) return;
    await controlService(service, action);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div><h1 className="text-2xl font-bold text-gray-900">System</h1><p className="mt-1 text-gray-500">Local installation health, diagnostics and optional advanced controls.</p></div>
        <div className="flex gap-2"><button onClick={() => void refreshAll()} disabled={isLoading} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50">{isLoading ? 'Refreshing…' : 'Refresh diagnostics'}</button><button onClick={() => void handleHealthCheck()} className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50">Run health check</button></div>
      </div>

      {error && <div className="flex items-center justify-between rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700"><span>{error.getUserMessage()}</span><button onClick={clearError} className="font-medium underline">Dismiss</button></div>}

      {setupStatus && !setupStatus.first_run_complete && <section className="rounded-xl border border-blue-200 bg-blue-50 p-5"><h2 className="font-semibold text-blue-950">First-run setup is in progress</h2><p className="mt-1 text-sm text-blue-800">The onboarding assistant checks local services, secure storage and the first profile. External accounts remain optional.</p></section>}

      <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-gray-200 bg-white p-4"><p className="text-sm text-gray-500">Version</p><p className="mt-1 font-semibold text-gray-900">{systemStatus?.version || systemConfig?.version || 'Checking'}</p></div>
        <div className="rounded-xl border border-gray-200 bg-white p-4"><p className="text-sm text-gray-500">Platform</p><p className="mt-1 font-semibold text-gray-900">{diagnostics?.platform || 'Checking'} · {diagnostics?.architecture || '—'}</p></div>
        <div className="rounded-xl border border-gray-200 bg-white p-4"><p className="text-sm text-gray-500">Free disk</p><p className="mt-1 font-semibold text-gray-900">{formatBytes(diagnostics?.disk.free_bytes)}</p></div>
        <div className="rounded-xl border border-gray-200 bg-white p-4"><p className="text-sm text-gray-500">Migrations</p><p className="mt-1 font-semibold text-gray-900">{diagnostics?.migrations.status || 'Checking'}</p></div>
      </section>

      <section><div className="mb-3 flex items-center justify-between"><div><h2 className="text-lg font-semibold text-gray-900">Local services</h2><p className="text-sm text-gray-500">Normal mode shows health without Docker internals.</p></div>{healthSummary !== null && <span className={`rounded-full px-3 py-1 text-sm font-medium ${healthSummary ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>{healthSummary ? 'Healthy' : 'Needs attention'}</span>}</div><div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">{Object.entries(services).map(([service, state]) => <article key={service} className="rounded-xl border border-gray-200 bg-white p-4"><div className="flex items-start justify-between"><div><h3 className="font-semibold text-gray-900">{SERVICE_LABELS[service] || service}</h3><p className="mt-1 text-sm text-gray-500">{state.error ? 'Health check returned a safe error classification.' : 'Local service status.'}</p></div><span className={`rounded-full px-2.5 py-1 text-xs font-medium ${STATUS_COLORS[state.status] || STATUS_COLORS.unknown}`}>{STATUS_LABELS[state.status] || state.status}</span></div>{advancedMode && controlAvailable && ['backend', 'postgres', 'n8n', 'playwright', 'frontend'].includes(service) && <div className="mt-4 flex gap-2 border-t pt-3"><button onClick={() => void handleControl(service as 'backend' | 'postgres' | 'n8n' | 'playwright' | 'frontend', 'start')} className="rounded bg-green-50 px-2 py-1 text-xs font-medium text-green-700 hover:bg-green-100">Start</button><button onClick={() => void handleControl(service as 'backend' | 'postgres' | 'n8n' | 'playwright' | 'frontend', 'restart')} className="rounded bg-yellow-50 px-2 py-1 text-xs font-medium text-yellow-700 hover:bg-yellow-100">Restart</button><button onClick={() => void handleControl(service as 'backend' | 'postgres' | 'n8n' | 'playwright' | 'frontend', 'stop')} className="rounded bg-red-50 px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-100">Stop</button></div>}</article>)}</div></section>

      <section className="rounded-xl border border-gray-200 bg-white p-5"><div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center"><div><h2 className="font-semibold text-gray-900">Advanced mode</h2><p className="mt-1 text-sm text-gray-500">Service actions are restricted to Automation Center containers and are disabled unless the local production runtime explicitly authorizes them.</p></div><label className="inline-flex items-center gap-2 text-sm font-medium text-gray-700"><input type="checkbox" checked={advancedMode} onChange={(event) => setAdvancedMode(event.target.checked)} className="h-4 w-4 rounded border-gray-300"/>Enable advanced mode</label></div><div className="mt-4 grid gap-3 text-sm sm:grid-cols-2"><div className="rounded-lg bg-gray-50 p-3"><p className="font-medium text-gray-700">Runtime controls</p><p className="mt-1 text-gray-500">{diagnostics?.local_service_control.message || 'Checking local runtime capability'}</p></div><div className="rounded-lg bg-gray-50 p-3"><p className="font-medium text-gray-700">Ports</p><p className="mt-1 text-gray-500">{diagnostics ? Object.values(diagnostics.ports).join(', ') : 'Checking preferred ports'}</p></div></div></section>
    </div>
  );
}
