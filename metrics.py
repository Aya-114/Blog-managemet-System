from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from threading import Lock
from time import time
from typing import Any


@dataclass
class MetricsStore:
    request_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    response_times: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))
    status_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    recent_errors: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=50))
    recent_logs: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=100))
    lock: Lock = field(default_factory=Lock)

    def record_request(self, method: str, path: str, status_code: int, duration_ms: float) -> None:
        key = f"{method} {path}"
        with self.lock:
            self.request_counts[key] += 1
            self.response_times[key].append(duration_ms)
            self.status_counts[str(status_code)] += 1
            if status_code >= 400:
                self.recent_errors.appendleft(
                    {
                        "timestamp": time(),
                        "path": path,
                        "method": method,
                        "status_code": status_code,
                        "message": "HTTP error response",
                    }
                )

    def record_error(self, method: str, path: str, message: str) -> None:
        with self.lock:
            self.recent_errors.appendleft(
                {
                    "timestamp": time(),
                    "path": path,
                    "method": method,
                    "status_code": 500,
                    "message": message,
                }
            )

    def record_log(self, level: str, message: str, extra: dict[str, Any] | None = None) -> None:
        with self.lock:
            self.recent_logs.appendleft(
                {
                    "timestamp": time(),
                    "level": level,
                    "message": message,
                    "extra": extra or {},
                }
            )

    def snapshot(self, cache_stats: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            total_requests = sum(self.request_counts.values())
            total_errors = sum(count for status, count in self.status_counts.items() if int(status) >= 400)
            route_metrics = []
            for route, count in sorted(self.request_counts.items()):
                times = self.response_times.get(route, [])
                average_ms = sum(times) / len(times) if times else 0
                route_metrics.append(
                    {
                        "route": route,
                        "request_count": count,
                        "average_response_ms": round(average_ms, 2),
                    }
                )
            return {
                "total_requests": total_requests,
                "error_count": total_errors,
                "error_rate": round(total_errors / total_requests, 4) if total_requests else 0,
                "status_counts": dict(self.status_counts),
                "routes": route_metrics,
                "recent_errors": list(self.recent_errors),
                "recent_logs": list(self.recent_logs),
                "cache": cache_stats,
            }

    def reset(self) -> None:
        with self.lock:
            self.request_counts.clear()
            self.response_times.clear()
            self.status_counts.clear()
            self.recent_errors.clear()
            self.recent_logs.clear()


metrics_store = MetricsStore()
