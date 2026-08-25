"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, api, type MeResponse } from "./api";

export function useMe() {
  const [me, setMe] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [unauthorized, setUnauthorized] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setMe(await api<MeResponse>("/api/v1/me"));
      setUnauthorized(false);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setUnauthorized(true);
        setMe(null);
      } else {
        setMe(null);
        setUnauthorized(false);
        setError("连接服务失败，请确认本地服务已启动后重试。");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Initial data loading is intentionally initiated when the hook is mounted.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh();
  }, [refresh]);

  return { me, loading, unauthorized, error, refresh };
}
