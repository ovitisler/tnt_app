import json
import os
import time
from typing import List, Dict, Any, Optional, Callable

from models.cache import CacheEntry

_KEY_PREFIX = "tnt:cache:"


def _make_key(sheet_name: str) -> str:
    return f"{_KEY_PREFIX}{sheet_name}"


def _get_redis():
    import redis
    return redis.from_url(os.environ['REDIS_URL'], decode_responses=True)


class RedisCacheManager:
    """CacheManager-compatible backend that stores data in Upstash Redis (Vercel KV).
    TTL is enforced by Redis expiry, so cache entries disappear automatically.
    Write-through (append_row/update_row) invalidates instead of patching in-place."""

    def get(self, sheet_name: str) -> Optional[CacheEntry]:
        raw = _get_redis().get(_make_key(sheet_name))
        if raw is None:
            return None
        stored = json.loads(raw)
        return CacheEntry(
            data=stored['data'],
            timestamp=stored['timestamp'],
            size_bytes=stored['size_bytes']
        )

    def has(self, sheet_name: str) -> bool:
        return _get_redis().exists(_make_key(sheet_name)) > 0

    def set(self, sheet_name: str, data: List[Dict[str, Any]], size_bytes: int, ttl: int = None):
        stored = json.dumps({'data': data, 'timestamp': time.time(), 'size_bytes': size_bytes})
        r = _get_redis()
        if ttl:
            r.set(_make_key(sheet_name), stored, ex=ttl)
        else:
            r.set(_make_key(sheet_name), stored)

    def append_row(self, sheet_name: str, row: Dict[str, Any]) -> bool:
        self.invalidate(sheet_name)
        print(f"[SHEETS] 📝 Redis cache invalidated for '{sheet_name}' (append)")
        return False

    def update_row(self, sheet_name: str, match_fn: Callable[[Dict], bool], updates: Dict[str, Any]) -> bool:
        self.invalidate(sheet_name)
        print(f"[SHEETS] 📝 Redis cache invalidated for '{sheet_name}' (update)")
        return False

    def invalidate(self, sheet_name: str = None):
        r = _get_redis()
        if sheet_name:
            r.delete(_make_key(sheet_name))
        else:
            keys = r.keys(f"{_KEY_PREFIX}*")
            if keys:
                r.delete(*keys)

    def keys(self) -> List[str]:
        return [k.replace(_KEY_PREFIX, '') for k in _get_redis().keys(f"{_KEY_PREFIX}*")]

    def items(self):
        for sheet_name in self.keys():
            entry = self.get(sheet_name)
            if entry:
                yield sheet_name, entry

    def clear(self):
        self.invalidate()
