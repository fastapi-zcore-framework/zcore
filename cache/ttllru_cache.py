import time

from collections import OrderedDict
from typing import Any, Optional

class TTLLRUCache:
    def __init__(self, maxsize: int = 1000):
        self.maxsize = maxsize
        self.cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()

    def get(self, key: str) -> Optional[Any]:
        if key not in self.cache:
            return None
        expiry, val = self.cache[key]
        if time.time() > expiry:
            del self.cache[key]
            return None
        self.cache.move_to_end(key)
        return val

    def set(self, key: str, value: Any, ttl: int = 3600):
        expiry = time.time() + ttl
        if key in self.cache:
            del self.cache[key]
        elif len(self.cache) >= self.maxsize:
            self.cache.popitem(last=False)
        self.cache[key] = (expiry, value)

    def delete(self, key: str):
        self.cache.pop(key, None)