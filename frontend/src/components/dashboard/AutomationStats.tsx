/**
 * Automation Stats component for Dashboard
 */


import type { Automation } from '../../types';

interface AutomationStatsProps {
  automations: Automation[];
}

export function AutomationStats({ automations }: AutomationStatsProps) {
  const stats = {
    total: automations.length,
    installed: automations.filter(a => a.status === 'installed').length,
    enabled: automations.filter(a => a.status === 'enabled').length,
    disabled: automations.filter(a => a.status === 'disabled').length,
    error: automations.filter(a => a.status === 'error').length,
    discovered: automations.filter(a => a.status === 'discovered').length,
  };

  const statItems = [
    { label: 'Total', value: stats.total, color: 'bg-blue-100 text-blue-800' },
    { label: 'Installed', value: stats.installed, color: 'bg-purple-100 text-purple-800' },
    { label: 'Enabled', value: stats.enabled, color: 'bg-green-100 text-green-800' },
    { label: 'Disabled', value: stats.disabled, color: 'bg-gray-100 text-gray-800' },
    { label: 'Error', value: stats.error, color: 'bg-red-100 text-red-800' },
    { label: 'Discovered', value: stats.discovered, color: 'bg-blue-100 text-blue-800' },
  ];

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h3 className="text-sm font-medium text-gray-900 mb-4">Automations</h3>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {statItems.map((stat) => (
          <div key={stat.label} className="text-center">
            <div className={`px-3 py-2 rounded-lg ${stat.color} text-2xl font-bold`}>
              {stat.value}
            </div>
            <p className="text-xs text-gray-500 mt-1">{stat.label}</p>
          </div>
        ))}
      </div>
    </div>
  );
}