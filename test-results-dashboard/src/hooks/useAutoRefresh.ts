import { useEffect, useRef, useState, useCallback } from 'react';

interface UseAutoRefreshOptions {
  /** Refresh interval in milliseconds, default 5000ms */
  interval?: number;
  /** Whether auto-refresh is enabled */
  enabled?: boolean;
}

export function useAutoRefresh<T>(
  fetchFn: () => Promise<T> | T,
  options: UseAutoRefreshOptions = {}
) {
  const { interval = 5000, enabled = true } = options;
  const [data, setData] = useState<T | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());
  const [isRefreshing, setIsRefreshing] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const fetchRef = useRef(fetchFn);

  fetchRef.current = fetchFn;

  const refresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const result = await fetchRef.current();
      setData(result);
      setLastRefreshed(new Date());
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    // Initial fetch
    refresh();
  }, [refresh]);

  useEffect(() => {
    if (!enabled) {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      return;
    }

    timerRef.current = setInterval(refresh, interval);

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [enabled, interval, refresh]);

  return { data, lastRefreshed, isRefreshing, refresh };
}
