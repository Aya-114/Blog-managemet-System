from __future__ import annotations

import fnmatch
import json
import time
from threading import Lock
from typing import Any

from app.core.config import settings

try:
    import redis
except ImportError:  # pragma: no cover - exercised when dependencies are absent
    redis = None


class CacheService:
    def __init__(self) -> None:
        self._client = None
        self._memory: dict[str, tuple[float, str]] = {}
        self._lock = Lock()
        self._force_memory = False
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.invalidations = 0

    def force_memory(self) -> None:
        self._force_memory = True
        self._client = None
        self.clear()

    def use_configured_backend(self) -> None:
        self._force_memory = False
        self._client = None
        self.clear()

    def _redis_client(self):
        if self._force_memory or settings.cache_backend.lower() == "memory" or redis is None:
            return None
        if self._client is None:
            try:
                self._client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
                self._client.ping()
            except Exception:
                self._client = None
        return self._client

    @property
    def backend_name(self) -> str:
        return "redis" if self._redis_client() else "memory"

    def get_json(self, key: str) -> Any | None:
        client = self._redis_client()
        if client:
            raw = client.get(key)
            if raw is None:
                self.misses += 1
                return None
            self.hits += 1
            return json.loads(raw)

        with self._lock:
            item = self._memory.get(key)
            if item is None:
                self.misses += 1
                return None
            expires_at, raw = item
            if expires_at < time.time():
                self._memory.pop(key, None)
                self.misses += 1
                return None
            self.hits += 1
            return json.loads(raw)

    def set_json(self, key: str, value: Any, ttl_seconds: int = 60) -> None:
        payload = json.dumps(value, default=str)
        client = self._redis_client()
        if client:
            client.setex(key, ttl_seconds, payload)
        else:
            with self._lock:
                self._memory[key] = (time.time() + ttl_seconds, payload)
        self.sets += 1

    def delete_pattern(self, pattern: str) -> None:
        client = self._redis_client()
        if client:
            for key in client.scan_iter(match=pattern):
                client.delete(key)
                self.invalidations += 1
            return

        with self._lock:
            for key in list(self._memory):
                if fnmatch.fnmatch(key, pattern):
                    self._memory.pop(key, None)
                    self.invalidations += 1

    def clear(self) -> None:
        with self._lock:
            self._memory.clear()
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.invalidations = 0

    def ping(self) -> dict[str, Any]:
        client = self._redis_client()
        if client:
            try:
                client.ping()
                return {"backend": "redis", "status": "ok"}
            except Exception as exc:
                return {"backend": "redis", "status": "error", "detail": str(exc)}
        return {"backend": "memory", "status": "ok"}

    def stats(self) -> dict[str, Any]:
        return {
            "backend": self.backend_name,
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "invalidations": self.invalidations,
        }


cache_service = CacheService()
