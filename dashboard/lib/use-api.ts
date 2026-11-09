"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/lib/api";

export function useApi<T>(path: string | null, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(Boolean(path));
  const [tick, setTick] = useState(0);
  const alive = useRef(true);

  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);

  useEffect(() => {
    if (!path) {
      setData(null);
      setLoading(false);
      setError(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    api<T>(path)
      .then((result) => {
        if (cancelled || !alive.current) return;
        setData(result);
        setError(null);
      })
      .catch((err) => {
        if (cancelled || !alive.current) return;
        setError(err instanceof Error ? err.message : "Failed to load");
      })
      .finally(() => {
        if (!cancelled && alive.current) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, tick, ...deps]);

  const reload = useCallback(() => setTick((value) => value + 1), []);

  return { data, error, loading, reload, setData };
}
