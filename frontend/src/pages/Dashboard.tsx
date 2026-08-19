/**
 * Dashboard page for Automation Center
 */

import { useEffect, useState } from 'react';
import { useAutomations } from '../hooks/useAutomations';
import { useExecutions } from '../hooks/useExecutions';
import { useSystem } from '../hooks/useSystem';
import { SystemStatusCard } from '../components/dashboard/SystemStatusCard';
import { AutomationStats } from '../components/dashboard/AutomationStats';
import { RecentExecutions } from '../components/dashboard/RecentExecutions';
import { ActiveProfileCard } from '../components/dashboard/ActiveProfileCard';


export function Dashboard() {
  const { automations, isLoading: automationsLoading, loadAutomations } = useAutomations();
  const { executions, isLoading: executionsLoading, loadExecutions } = useExecutions();
  const { systemStatus, isLoading: systemLoading, loadSystemStatus } = useSystem();

  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await Promise.all([
      loadAutomations(),
      loadExecutions(),
      loadSystemStatus(),
    ]);
    setIsRefreshing(false);
  };

  useEffect(() => {
    handleRefresh();
  }, []);

  const services = [
    { key: 'postgres', label: 'PostgreSQL' },
    { key: 'n8n', label: 'n8n' },
    { key: 'playwright', label: 'Playwright' },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 mt-1">Overview of your automation center</p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={isRefreshing}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors flex items-center space-x-2"
        >
          <svg className={`w-5 h-5 ${isRefreshing ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          <span>{isRefreshing ? 'Refreshing...' : 'Refresh'}</span>
        </button>
      </div>

      {/* Active Profile */}
      <section>
        <ActiveProfileCard />
      </section>

      {/* System Status */}
      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">System Status</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {services.map((service) => (
            <SystemStatusCard
              key={service.key}
              service={service.key}
              status={systemStatus?.services[service.key as keyof typeof systemStatus.services]}
              label={service.label}
            />
          ))}
        </div>
      </section>

      {/* Automation Stats */}
      <section>
        <AutomationStats automations={automations} />
      </section>

      {/* Recent Executions */}
      <section>
        <RecentExecutions executions={executions} />
      </section>

      {/* Loading States */}
      {(automationsLoading || executionsLoading || systemLoading) && (
        <div className="fixed inset-0 bg-white/80 flex items-center justify-center z-50">
          <div className="flex items-center space-x-2">
            <svg className="animate-spin h-8 w-8 text-blue-600" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <span className="text-gray-700">Loading dashboard...</span>
          </div>
        </div>
      )}
    </div>
  );
}