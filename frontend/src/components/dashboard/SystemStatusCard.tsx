/**
 * System Status Card component for Dashboard
 */

import { STATUS_COLORS, STATUS_LABELS } from '../../types';

interface SystemStatusCardProps {
  service: string;
  status: { status: string; error?: string } | undefined;
  label: string;
}

export function SystemStatusCard({ service, status, label }: SystemStatusCardProps) {
  const serviceStatus = status?.status || 'unknown';
  const error = status?.error;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium text-gray-900 capitalize">{label}</h3>
          <p className="text-xs text-gray-500 mt-1">{service}</p>
        </div>
        <span className={`px-3 py-1 text-sm font-medium rounded-full ${STATUS_COLORS[serviceStatus] || STATUS_COLORS.unknown}`}>
          {STATUS_LABELS[serviceStatus] || serviceStatus}
        </span>
      </div>
      {error && (
        <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-md">
          <p className="text-xs text-red-700">{error}</p>
        </div>
      )}
    </div>
  );
}