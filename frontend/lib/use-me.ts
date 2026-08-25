"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type MeResponse } from "./api";

export function useMe() {
  const [me, setMe] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setMe(await api<MeResponse>("/api/v1/me"));
    } catch {
      setMe(null);
      setError("连接服务失败，请确认本地服务已启动后重试。");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Initial data loading is intentionally initiated when the hook is mounted.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh();
  }, [refresh]);

  return { me, loading, error, refresh };
}
