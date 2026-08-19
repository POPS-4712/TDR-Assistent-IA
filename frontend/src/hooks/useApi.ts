/**
 * Custom hooks for API calls with loading states and error handling
 */

import { useState, useCallback, useRef } from 'react';
import { ApiError } from '../api/client';

export interface UseApiState<T> {
  data: T | null;
  isLoading: boolean;
  error: ApiError | null;
}

export interface UseApiActions<T> {
  execute: (...args: unknown[]) => Promise<T | null>;
  reset: () => void;
  setData: (data: T) => void;
  setError: (error: ApiError | null) => void;
}

export type UseApiReturn<T> = UseApiState<T> & UseApiActions<T>;

export function useApi<T>(
  apiFunction: (...args: unknown[]) => Promise<T>,
  options?: {
    immediate?: boolean;
    args?: unknown[];
    onSuccess?: (data: T) => void;
    onError?: (error: ApiError) => void;
  }
): UseApiReturn<T> {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const isMounted = useRef(true);

  const execute = useCallback(
    async (...args: unknown[]): Promise<T | null> => {
      if (!isMounted.current) return null;
      
      setIsLoading(true);
      setError(null);
      
      try {
        const result = await apiFunction(...args);
        if (isMounted.current) {
          setData(result);
          options?.onSuccess?.(result);
        }
        return result;
      } catch (err) {
        const apiError = err instanceof ApiError ? err : ApiError.networkError(String(err));
        if (isMounted.current) {
          setError(apiError);
          options?.onError?.(apiError);
        }
        return null;
      } finally {
        if (isMounted.current) {
          setIsLoading(false);
        }
      }
    },
    [apiFunction, options]
  );

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setIsLoading(false);
  }, []);

  // Execute immediately if requested
  // Note: We don't use useEffect here to avoid stale closures
  // The caller should call execute() manually or use a separate hook

  return {
    data,
    isLoading,
    error,
    execute,
    reset,
    setData,
    setError,
  };
}

export function useAsyncState<T>(
  initialData: T | null = null
): UseApiState<T> & { setData: (data: T) => void; setError: (error: ApiError | null) => void; setLoading: (loading: boolean) => void } {
  const [data, setData] = useState<T | null>(initialData);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  return {
    data,
    isLoading,
    error,
    setData,
    setError,
    setLoading: setIsLoading,
  };
}