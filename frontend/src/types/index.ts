/**
 * TypeScript types for Automation Center Frontend
 * Matches backend API schemas
 */

// ============================================
// System Types
// ============================================

export interface ServiceStatus {
  status: 'healthy' | 'unhealthy' | 'running' | 'starting' | 'stopped' | 'error' | 'not_managed' | 'unknown';
  error?: string;
}

export interface SystemStatus {
  app_name: string;
  version: string;
  environment: string;
  first_run_complete: boolean;
  services: Record<string, ServiceStatus>;
}

export interface SystemConfig {
  app_name: string;
  version: string;
  environment: string;
  portable_mode: boolean;
  user_data_dir_configured: boolean;
  n8n_api_url: string;
  playwright_api_url: string;
}

export interface SetupStatus {
  first_run_complete: boolean;
  user_data_dir_configured: boolean;
  runtime_ready: boolean;
  services: Record<string, ServiceStatus>;
  external_accounts_optional: boolean;
  profile_required_for_completion: boolean;
}

export interface SystemDiagnostics {
  app_name: string;
  version: string;
  platform: string;
  architecture: string;
  environment: string;
  first_run_complete: boolean;
  services: Record<string, ServiceStatus>;
  local_service_control: { enabled: boolean; available: boolean; message: string };
  managed_container_statuses: Record<string, { status: string; container_present: boolean }>;
  disk: { free_bytes: number; total_bytes: number };
  ports: Record<string, number>;
  migrations: { enabled: boolean; status: string };
}

export interface ServiceControlResult {
  service: string;
  action: 'start' | 'stop' | 'restart';
  success: boolean;
  status: string;
  message: string;
}

// ============================================
// Automation Types
// ============================================

export type AutomationStatus = 
  | 'discovered' 
  | 'ready'
  | 'installing'
  | 'installed' 
  | 'enabled' 
  | 'disabled'
  | 'blocked'
  | 'error';

export interface Automation {
  id: string;
  name: string;
  description: string;
  version: string;
  status: AutomationStatus;
  manifest_url?: string;
  dependencies: string[];
  n8n_workflow_id?: string;
  category?: string;
  created_at: string;
  updated_at: string;
}

export interface AutomationListResponse {
  automations: Automation[];
  total: number;
}

export interface AutomationDetailResponse {
  automation: Automation;
}

export interface AutomationPreflightCheck {
  name: string;
  status: 'pass' | 'blocked' | 'error';
  details: unknown;
}

export interface AutomationAccountResolution {
  provider: string;
  account: string | null;
  status: string;
  scopes: { required: string[]; granted: string[] };
  validation_status: 'valid' | 'blocked' | 'invalid' | 'missing';
  missing_requirements: string[];
  compatible: boolean;
}

export interface AutomationCredentialMapping {
  provider: string;
  required_n8n_type: string;
  account: string | null;
  status: 'compatible' | 'missing_compatible_mapping';
  compatible: boolean;
  missing_requirements: string[];
}

export interface AutomationPreflightResult {
  automation_id: string;
  status: 'ready' | 'blocked' | 'error';
  checks: AutomationPreflightCheck[];
  requirements: Array<{ provider: string; scopes: string[]; type: string }>;
  accounts?: AutomationAccountResolution[];
  credential_mappings?: AutomationCredentialMapping[];
  missing_requirements?: string[];
  runtime_dependencies?: string[];
  profile_compatibility?: { status: 'optional' | 'required' | 'blocked' };
  supports_profile_execution: boolean;
  mutations_applied: false;
}

export interface InstallAutomationResult {
  success: boolean;
  automation_id: string;
  n8n_workflow_id?: string;
  message?: string;
  steps?: InstallationStep[];
}

export interface InstallationStep {
  step: number;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  message?: string;
}

export interface EnableAutomationResult {
  success: boolean;
  automation_id: string;
  message?: string;
}

export interface DisableAutomationResult {
  success: boolean;
  automation_id: string;
  message?: string;
}

export interface UninstallAutomationResult {
  success: boolean;
  automation_id: string;
  message?: string;
}

export interface AutomationLog {
  id: string;
  automation_id: string;
  profile_id?: string | null;
  workflow_id?: string;
  n8n_execution_id?: string;
  status: ExecutionStatus;
  started_at: string;
  completed_at?: string;
  duration_ms?: number;
  error_message?: string;
  result?: { tracked: boolean };
}

export interface AutomationLogsResponse {
  automation_id: string;
  logs: AutomationLog[];
  total: number;
}

export interface UpdateCheckResponse {
  updates: Array<{
    automation_id: string;
    current_version: string;
    available_version: string;
    update_available: boolean;
  }>;
  total: number;
}

// ============================================
// Credential Types
// ============================================

export type CredentialStatus = 
  | 'active' 
  | 'expired' 
  | 'revoked' 
  | 'error' 
  | 'disconnected'
  | 'reauth_required';

export type CredentialType = 'oauth' | 'api_key' | 'token' | 'structured';

export interface Credential {
  id: string;
  provider: string;
  account_identifier: string;
  scopes: string[];
  status: CredentialStatus;
  metadata: Record<string, unknown>;
  last_refresh?: string;
  last_validation?: string;
  expires_at?: string;
  created_at: string;
  updated_at: string;
}

export interface CredentialListResponse {
  credentials: Credential[];
  total: number;
}

export interface CredentialDetailResponse {
  credential: Credential;
}

export interface Provider {
  name: string;
  display_name: string;
  credential_type: CredentialType;
  scopes?: string[];
  description?: string;
}

export interface ProvidersResponse {
  providers: Provider[];
}

export interface ConnectCredentialRequest {
  provider: string;
  scopes?: string[];
}

export interface ConnectCredentialResponse {
  type: 'oauth' | 'api_key' | 'token' | 'structured';
  auth_url?: string;
  state?: string;
  message?: string;
  provider: string;
}

export interface ApiKeyRequest {
  provider: string;
  account_identifier: string;
  api_key: string;
}

export interface TokenRequest {
  provider: string;
  account_identifier: string;
  token: string;
}

export interface StructuredCredentialRequest {
  provider: string;
  account_identifier: string;
  secrets: Record<string, string>;
  metadata: Record<string, unknown>;
}

export interface StoreCredentialResponse {
  success: boolean;
  credential_id: string;
  provider: string;
  account_identifier: string;
  status: CredentialStatus;
  metadata?: Record<string, unknown>;
  message?: string;
}

export interface CredentialValidationResponse {
  credential_id: string;
  result: 'VALID' | 'INVALID' | 'EXPIRED' | 'REAUTH_REQUIRED';
  status: CredentialStatus;
}

export interface RefreshCredentialResponse {
  success: boolean;
  credential_id: string;
  message?: string;
}

export interface RevokeCredentialResponse {
  success: boolean;
  credential_id: string;
  message?: string;
}

export interface OAuthCallbackResponse {
  success: boolean;
  credential_id: string;
  provider: string;
  account_identifier: string;
  message?: string;
}

// ============================================
// Execution Types
// ============================================

export type ExecutionStatus = 
  | 'queued'
  | 'running' 
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface Execution {
  id: string;
  automation_id: string;
  profile_id?: string | null;
  workflow_id?: string;
  n8n_execution_id?: string;
  status: ExecutionStatus;
  started_at: string;
  completed_at?: string;
  duration_ms?: number;
  error_message?: string;
  result?: { tracked: boolean };
}

export interface RunAutomationResult {
  success: boolean;
  automation_id: string;
  execution_id: string;
  n8n_execution_id?: string;
  profile_id?: string | null;
  status: ExecutionStatus;
}

export interface ExecutionListResponse {
  executions: Execution[];
  total: number;
}

export interface ExecutionDetailResponse {
  execution: Execution;
}

export interface RerunExecutionResponse {
  success: boolean;
  execution_id: string;
  new_execution_id?: string;
  message?: string;
}

// ============================================
// API Error Types
// ============================================

export interface APIError {
  status: number;
  message: string;
  detail?: string;
}

export interface APIErrorResponse {
  detail: string;
}

// ============================================
// UI State Types
// ============================================

export interface LoadingState {
  isLoading: boolean;
  error?: string;
}

export interface AsyncState<T> extends LoadingState {
  data?: T;
}

export type ButtonState = 'idle' | 'loading' | 'success' | 'error';

export interface ButtonStateConfig {
  state: ButtonState;
  label: string;
  disabled: boolean;
}

// ============================================
// Form Types
// ============================================

export interface ConnectProviderFormData {
  provider: string;
  api_key?: string;
  token?: string;
}

export interface ConfirmDialogProps {
  isOpen: boolean;
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'danger' | 'warning' | 'info';
}

// ============================================
// WebSocket Types (for future use)
// ============================================

export interface WebSocketMessage {
  type: 'execution_started' | 'execution_completed' | 'automation_status_changed' | 'credential_status_changed';
  payload: unknown;
  timestamp: string;
}

// ============================================
// Utility Types
// ============================================

export type StatusColorMap = Record<string, string>;

export const STATUS_COLORS: StatusColorMap = {
  // System status
  healthy: 'bg-green-100 text-green-800',
  unhealthy: 'bg-red-100 text-red-800',
  starting: 'bg-blue-100 text-blue-800 animate-pulse',
  stopped: 'bg-gray-100 text-gray-800',
  not_managed: 'bg-gray-100 text-gray-800',
  degraded: 'bg-yellow-100 text-yellow-800',
  offline: 'bg-red-100 text-red-800',
  unknown: 'bg-gray-100 text-gray-800',
  
  // Automation status
  discovered: 'bg-blue-100 text-blue-800',
  ready: 'bg-teal-100 text-teal-800',
  installing: 'bg-indigo-100 text-indigo-800 animate-pulse',
  installed: 'bg-purple-100 text-purple-800',
  enabled: 'bg-green-100 text-green-800',
  disabled: 'bg-gray-100 text-gray-800',
  error: 'bg-red-100 text-red-800',
  blocked: 'bg-yellow-100 text-yellow-800',
  
  // Credential status
  active: 'bg-green-100 text-green-800',
  expired: 'bg-yellow-100 text-yellow-800',
  revoked: 'bg-red-100 text-red-800',
  disconnected: 'bg-gray-100 text-gray-800',
  reauth_required: 'bg-yellow-100 text-yellow-800',
  
  // Execution status
  queued: 'bg-gray-100 text-gray-800',
  running: 'bg-blue-100 text-blue-800 animate-pulse',
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
  success: 'bg-green-100 text-green-800',
  cancelled: 'bg-gray-100 text-gray-800',
};

export const STATUS_LABELS: Record<string, string> = {
  // System status
  healthy: 'Healthy',
  unhealthy: 'Unhealthy',
  starting: 'Starting',
  stopped: 'Stopped',
  not_managed: 'Managed externally',
  degraded: 'Degraded',
  offline: 'Offline',
  unknown: 'Unknown',
  
  // Automation status
  discovered: 'Discovered',
  ready: 'Ready to install',
  installing: 'Installing',
  installed: 'Installed',
  enabled: 'Enabled',
  disabled: 'Disabled',
  error: 'Error',
  blocked: 'Bloqueada',
  
  // Credential status
  active: 'Connected',
  expired: 'Expired',
  revoked: 'Revoked',
  disconnected: 'Desconectada',
  reauth_required: 'Reautorización necesaria',
  credential_error: 'Error',
  
  // Execution status
  queued: 'Queued',
  running: 'Running',
  completed: 'Completed',
  failed: 'Failed',
  success: 'Success',
  cancelled: 'Cancelled',
};
