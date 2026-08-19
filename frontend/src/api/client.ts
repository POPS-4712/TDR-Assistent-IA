/**
 * Centralized HTTP API Client for Automation Center
 * Base URL: http://localhost:8000/api/v1
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
const API_ORIGIN = API_BASE_URL.startsWith('/')
  ? (typeof window === 'undefined' ? 'http://localhost' : window.location.origin)
  : undefined;
const DEFAULT_TIMEOUT = 30000; // 30 seconds

let authToken: string | null = null;

export function setAuthToken(token: string | null): void {
  authToken = token;
}

export function getAuthToken(): string | null {
  return authToken;
}

export interface RequestOptions extends RequestInit {
  timeout?: number;
  params?: Record<string, string | number | boolean | undefined>;
}

export interface ApiResponse<T> {
  data: T;
  status: number;
  headers: Headers;
}

export class ApiError extends Error {
  public readonly status: number;
  public readonly detail?: string;
  public readonly isNetworkError: boolean;
  public readonly isTimeout: boolean;

  constructor(
    message: string,
    status: number,
    detail?: string,
    isNetworkError = false,
    isTimeout = false
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    this.isNetworkError = isNetworkError;
    this.isTimeout = isTimeout;
  }

  static fromResponse(response: Response, detail?: string): ApiError {
    const status = response.status;
    let message = `HTTP ${status}: ${response.statusText}`;
    
    switch (status) {
      case 400:
        message = 'Bad Request';
        break;
      case 401:
        message = 'Unauthorized';
        break;
      case 403:
        message = 'Forbidden';
        break;
      case 404:
        message = 'Not Found';
        break;
      case 409:
        message = 'Conflict';
        break;
      case 422:
        message = 'Validation Error';
        break;
      case 500:
        message = 'Internal Server Error';
        break;
      case 503:
        message = 'Service Unavailable';
        break;
      default:
        message = `HTTP ${status}: ${response.statusText}`;
    }

    return new ApiError(message, status, detail);
  }

  static networkError(message = 'Network error'): ApiError {
    return new ApiError(message, 0, undefined, true);
  }

  static timeoutError(message = 'Request timeout'): ApiError {
    return new ApiError(message, 0, undefined, false, true);
  }

  getUserMessage(): string {
    if (this.isNetworkError) {
      return 'Unable to connect to the server. Please check your connection.';
    }
    if (this.isTimeout) {
      return 'Request timed out. Please try again.';
    }
    
    switch (this.status) {
      case 400:
        return 'Invalid request. Please check your input.';
      case 401:
        return 'Your session has expired. Please log in again.';
      case 403:
        return 'You do not have permission to perform this action.';
      case 404:
        return 'The requested resource was not found.';
      case 409:
        return 'A conflict occurred. The resource may already exist.';
      case 422:
        return 'Validation failed. Please check your input.';
      case 500:
        return 'An unexpected error occurred. Please try again later.';
      case 503:
        return 'Service is temporarily unavailable. Please try again later.';
      default:
        return this.message || 'An error occurred. Please try again.';
    }
  }
}

function buildUrl(endpoint: string, params?: Record<string, string | number | boolean | undefined>): string {
  const url = new URL(`${API_BASE_URL}${endpoint}`, API_ORIGIN);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.append(key, String(value));
      }
    });
  }
  return url.toString();
}

async function fetchWithTimeout(
  url: string,
  options: RequestInit,
  timeout: number
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...options.headers as Record<string, string>,
  };

  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers,
    });
    return response;
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw ApiError.timeoutError();
    }
    throw ApiError.networkError();
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<ApiResponse<T>> {
  const { timeout = DEFAULT_TIMEOUT, params, ...fetchOptions } = options;
  const url = buildUrl(endpoint, params);

  const response = await fetchWithTimeout(url, fetchOptions, timeout);

  let data: T;
  const contentType = response.headers.get('content-type');
  
  if (contentType?.includes('application/json')) {
    data = await response.json();
  } else {
    data = await response.text() as unknown as T;
  }

  if (!response.ok) {
    const detail = typeof data === 'object' && data !== null && 'detail' in data
      ? String((data as Record<string, unknown>).detail)
      : undefined;
    throw ApiError.fromResponse(response, detail);
  }

  return { data, status: response.status, headers: response.headers };
}

// Convenience methods
export const api = {
  get: <T>(endpoint: string, options?: RequestOptions) =>
    apiRequest<T>(endpoint, { ...options, method: 'GET' }),

  post: <T>(endpoint: string, body: unknown, options?: RequestOptions) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: 'POST',
      body: JSON.stringify(body),
    }),

  put: <T>(endpoint: string, body: unknown, options?: RequestOptions) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: JSON.stringify(body),
    }),

  patch: <T>(endpoint: string, body: unknown, options?: RequestOptions) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: JSON.stringify(body),
    }),

  delete: <T>(endpoint: string, options?: RequestOptions) =>
    apiRequest<T>(endpoint, { ...options, method: 'DELETE' }),
};

export default api;