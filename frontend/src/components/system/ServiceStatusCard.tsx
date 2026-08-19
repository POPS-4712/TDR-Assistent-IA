/**
 * Service Status Card component for System page
 */

import { STATUS_COLORS, STATUS_LABELS } from '../../types';

interface ServiceStatusCardProps {
  service: string;
  status: { status: string; error?: string } | undefined;
  label: string;
  description?: string;
}

export function ServiceStatusCard({ service, status, label, description }: ServiceStatusCardProps) {
  const serviceStatus = status?.status || 'unknown';
  const error = status?.error;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center text-xl">
            {service === 'postgres' && '🐘'}
            {service === 'n8n' && '⚙️'}
            {service === 'playwright' && '🎭'}
          </div>
          <div>
            <h3 className="text-lg font-medium text-gray-900">{label}</h3>
            {description && <p className="text-sm text-gray-500 mt-1">{description}</p>}
          </div>
        </div>
        <span className={`px-3 py-1 text-sm font-medium rounded-full ${STATUS_COLORS[serviceStatus] || STATUS_COLORS.unknown}`}>
          {STATUS_LABELS[serviceStatus] || serviceStatus}
        </span>
      </div>
      {error && (
        <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-md">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}
    </div>
  );
}