/**
 * Automations page for Automation Center
 */

import { useState } from 'react';
import { useAutomations } from '../hooks/useAutomations';
import { AutomationCard } from '../components/automations/AutomationCard';

export function Automations() {
  const { 
        automations, 
    preflightById,
    isLoading, 
    error, 
    installState,
    loadAutomations, 
    installAutomation,
    enableAutomation,
    disableAutomation,
    uninstallAutomation,
    runAutomation,
    clearError,

  } = useAutomations();

  const [filter, setFilter] = useState<'all' | 'discovered' | 'ready' | 'installing' | 'installed' | 'enabled' | 'disabled' | 'blocked' | 'error'>('all');

  const filteredAutomations = automations.filter(auto => 
    filter === 'all' || auto.status === filter
  );

  const handleInstall = async (id: string) => {
    await installAutomation(id);
  };

  const handleEnable = async (id: string) => {
    try {
      await enableAutomation(id);
    } catch (err) {
      // Error handled in hook
    }
  };

  const handleDisable = async (id: string) => {
    try {
      await disableAutomation(id);
    } catch (err) {
      // Error handled in hook
    }
  };

    const handleRun = async (id: string) => {
    if (window.confirm('Run this enabled automation now using the active profile, if one is configured?')) {
      await runAutomation(id);
    }
  };

  const handleUninstall = async (id: string) => {

    if (window.confirm('Are you sure you want to uninstall this automation?')) {
      try {
        await uninstallAutomation(id);
      } catch (err) {
        // Error handled in hook
      }
    }
  };

  const handleRetry = async (id: string) => {
    await installAutomation(id);
  };

  

  const statusFilters = [
    { value: 'all', label: 'All' },
    { value: 'discovered', label: 'Discovered' },
    { value: 'ready', label: 'Ready' },
    { value: 'installing', label: 'Installing' },
    { value: 'installed', label: 'Installed' },
    { value: 'enabled', label: 'Enabled' },
    { value: 'disabled', label: 'Disabled' },
    { value: 'blocked', label: 'Blocked' },
    { value: 'error', label: 'Error' },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Automations</h1>
          <p className="text-gray-500 mt-1">Manage your automation workflows</p>
        </div>
        <div className="flex items-center space-x-3">
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as typeof filter)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {statusFilters.map((f) => (
              <option key={f.value} value={f.value}>{f.label}</option>
            ))}
          </select>
          <button
                        onClick={loadAutomations}

            disabled={isLoading}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            Refresh checks
          </button>
        </div>
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

      {/* Automations Grid */}
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
      ) : filteredAutomations.length === 0 ? (
        <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">No automations found</h3>
          <p className="mt-1 text-sm text-gray-500">
            {filter === 'all' 
                            ? 'Automatic checks are loading available automations.' 
 
              : `No automations with status "${filter}".`}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredAutomations.map((automation) => (
            <AutomationCard
              key={automation.id}
                            automation={automation}
              preflight={preflightById[automation.id]}
              installState={installState[automation.id]}

              onInstall={handleInstall}
              onEnable={handleEnable}
                            onDisable={handleDisable}
              onRun={handleRun}
              onUninstall={handleUninstall}

              onRetry={handleRetry}
            />
          ))}
        </div>
      )}
    </div>
  );
}