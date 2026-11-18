import { useState, useEffect, useCallback } from 'react';
import { pathsnapService, HealthCheckResult } from '../services/pathsnapService';
import { getStoredBaseUrl } from '../services/apiClient';

export function useBackendHealth(pollIntervalMs: number = 10000) {
  const [result, setResult] = useState<HealthCheckResult>({
    isHealthy: false,
    latencyMs: 0,
    urlChecked: getStoredBaseUrl(),
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const checkStatus = useCallback(async (customUrl?: string) => {
    setIsLoading(true);
    const res = await pathsnapService.checkHealth(customUrl);
    setResult(res);
    setIsLoading(false);
    return res;
  }, []);

  useEffect(() => {
    checkStatus();
    if (pollIntervalMs > 0) {
      const interval = setInterval(() => {
        checkStatus();
      }, pollIntervalMs);
      return () => clearInterval(interval);
    }
  }, [checkStatus, pollIntervalMs]);

  return {
    ...result,
    isLoading,
    refresh: checkStatus,
  };
}
