"""登录限流。

MVP 阶段使用进程内滑动窗口限流；按调用方提供的 key（通常是客户端 IP）计数。
多进程/多实例部署前需替换为共享存储实现。
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class SlidingWindowRateLimiter:
    """固定窗口大小 + 记录每次尝试时间戳的滑动窗口限流器。"""

    def __init__(self, window_seconds: int, max_attempts: int) -> None:
        self.window_seconds = window_seconds
        self.max_attempts = max_attempts
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        """尝试占用一次额度；在窗口内未超限返回 True，否则 False。"""
        now = time.monotonic()
        with self._lock:
            window = self._attempts[key]
            cutoff = now - self.window_seconds
            while window and window[0] <= cutoff:
                window.popleft()
            if len(window) >= self.max_attempts:
                return False
            window.append(now)
            return True

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._attempts.clear()
            else:
                self._attempts.pop(key, None)
