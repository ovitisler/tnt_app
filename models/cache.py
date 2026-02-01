import json
import time
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Callable


@dataclass
class CacheEntry:
    """Represents a cached sheet's data"""
    data: List[Dict[str, Any]]
    timestamp: float
    size_bytes: int

    def age(self) -> float:
        """Returns how old this cache entry is in seconds"""
        return time.time() - self.timestamp

    def is_stale(self, ttl: int) -> bool:
        """Returns True if cache has exceeded its TTL"""
        return self.age() >= ttl

    def is_fresh(self, ttl: int) -> bool:
        """Returns True if cache is within its TTL"""
        return self.age() < ttl

    def mark_fresh(self):
        """Update timestamp to current time"""
        self.timestamp = time.time()

    def add_row(self, row: Dict[str, Any]):
        """Append a row and update size estimate"""
        self.data.append(row)
        self.size_bytes += len(json.dumps(row).encode('utf-8'))
        self.mark_fresh()


class CacheManager:
    """Manages the cache for all sheets"""

    def __init__(self):
        self._cache: Dict[str, CacheEntry] = {}

    def get(self, sheet_name: str) -> Optional[CacheEntry]:
        """Get a cache entry, or None if not cached"""
        return self._cache.get(sheet_name)

    def has(self, sheet_name: str) -> bool:
        """Check if a sheet is cached"""
        return sheet_name in self._cache

    def set(self, sheet_name: str, data: List[Dict[str, Any]], size_bytes: int):
        """Create or replace a cache entry"""
        self._cache[sheet_name] = CacheEntry(
            data=data,
            timestamp=time.time(),
            size_bytes=size_bytes
        )

    def append_row(self, sheet_name: str, row: Dict[str, Any]) -> bool:
        """Append a row to cached data (write-through). Returns True if successful."""
        if sheet_name in self._cache:
            self._cache[sheet_name].add_row(row)
            print(f"[SHEETS] 📝 Cache updated for '{sheet_name}' (append)")
            return True
        else:
            print(f"[SHEETS] ⚠️ No cache for '{sheet_name}' - write-through skipped")
            return False

    def update_row(self, sheet_name: str, match_fn: Callable[[Dict], bool], updates: Dict[str, Any]) -> bool:
        """Update a row in cached data (write-through). Returns True if row was found and updated."""
        if sheet_name not in self._cache:
            print(f"[SHEETS] ⚠️ No cache for '{sheet_name}' - write-through skipped")
            return False

        cached = self._cache[sheet_name]
        for row in cached.data:
            if match_fn(row):
                row.update(updates)
                cached.mark_fresh()
                print(f"[SHEETS] 📝 Cache updated for '{sheet_name}' (update)")
                return True

        print(f"[SHEETS] ⚠️ No matching row found in cache for '{sheet_name}'")
        return False

    def invalidate(self, sheet_name: Optional[str] = None):
        """Invalidate cache. If sheet_name is None, invalidates all."""
        if sheet_name:
            if sheet_name in self._cache:
                del self._cache[sheet_name]
        else:
            self._cache.clear()

    def keys(self) -> List[str]:
        """Get list of cached sheet names"""
        return list(self._cache.keys())

    def items(self):
        """Iterate over (sheet_name, CacheEntry) pairs"""
        return self._cache.items()

    def clear(self):
        """Clear all cache entries"""
        self._cache.clear()
