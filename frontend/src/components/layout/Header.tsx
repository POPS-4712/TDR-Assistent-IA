/**
 * Header component for Automation Center
 */

import { useNavigate, useLocation } from 'react-router-dom';
import { STATUS_LABELS } from '../../types';
import { ProfileSelector } from '../../pages/Profiles/ProfileSelector';

interface HeaderProps {
  systemStatus?: {
    services: Record<string, { status: string; error?: string }>;
  };
}

export function Header({ systemStatus }: HeaderProps) {
  const navigate = useNavigate();
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'Dashboard', icon: '📊' },
    { path: '/profiles', label: 'Profiles', icon: '👤' },
    { path: '/automations', label: 'Automations', icon: '⚙️' },
    { path: '/accounts', label: 'Accounts', icon: '🔐' },
    { path: '/executions', label: 'Executions', icon: '▶️' },
    { path: '/system', label: 'System', icon: '🖥️' },
  ];

  const getServiceStatus = (service: string) => {
    const status = systemStatus?.services[service]?.status || 'unknown';
    return STATUS_LABELS[status] || status;
  };

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo and Navigation */}
          <div className="flex items-center space-x-8">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">AC</span>
              </div>
              <h1 className="text-xl font-semibold text-gray-900">Automation Center</h1>
            </div>

            <nav className="hidden md:flex items-center space-x-1">
              {navItems.map((item) => (
                <button
                  key={item.path}
                  onClick={() => navigate(item.path)}
                  className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    location.pathname === item.path
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                  }`}
                >
                  <span>{item.icon}</span>
                  <span>{item.label}</span>
                </button>
              ))}
            </nav>
          </div>

          {/* System Status Indicators */}
          <div className="flex items-center space-x-4">
            <div className="hidden xl:block w-48">
              <ProfileSelector compact />
            </div>
            {systemStatus && (
              <div className="hidden sm:flex items-center space-x-3">
                {['postgres', 'n8n', 'playwright'].map((service) => (
                  <div key={service} className="flex items-center space-x-1">
                    <span className="text-xs text-gray-500 capitalize">{service}</span>
                    <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                      systemStatus.services[service]?.status === 'healthy'
                        ? 'bg-green-100 text-green-800'
                        : systemStatus.services[service]?.status === 'degraded'
                        ? 'bg-yellow-100 text-yellow-800'
                        : systemStatus.services[service]?.status === 'offline'
                        ? 'bg-red-100 text-red-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {getServiceStatus(service)}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {/* Mobile menu button */}
            <button className="md:hidden p-2 rounded-lg text-gray-600 hover:bg-gray-100">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}