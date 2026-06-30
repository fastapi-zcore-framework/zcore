import time
import threading
import weakref
from collections import OrderedDict
from typing import Any, Optional, List, Set

_active_caches: weakref.WeakSet["TTLLRUCache"] = weakref.WeakSet()

class TTLLRUCache:
    def __init__(self, maxsize: int = 1000) -> None:
        self.maxsize = maxsize
        self.cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = threading.Lock()
        _active_caches.add(self)

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self.cache:
                return None
            expiry, val = self.cache[key]
            if time.time() > expiry:
                self.cache.pop(key, None)
                return None
            self.cache.move_to_end(key)
            return val

    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        expiry = time.time() + ttl
        with self._lock:
            if key in self.cache:
                self.cache.pop(key, None)
            elif len(self.cache) >= self.maxsize:
                self.cache.popitem(last=False)
            self.cache[key] = (expiry, value)

    def delete(self, key: str) -> None:
        with self._lock:
            self.cache.pop(key, None)

    def evict_expired(self) -> None:
        now = time.time()
        expired_keys: List[str] = []
        with self._lock:
            for k, (expiry, _) in self.cache.items():
                if now > expiry:
                    expired_keys.append(k)
            for k in expired_keys:
                self.cache.pop(k, None)

    @classmethod
    def evict_all_expired(cls) -> None:
        for cache_instance in list(_active_caches):
            try:
                cache_instance.evict_expired()
            except ReferenceError:
                pass