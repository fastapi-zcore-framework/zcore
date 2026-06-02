import json
import logging

from typing import Any, Optional

from app.core.cache.ttllru_cache import TTLLRUCache
from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

class BaseCache:
    def __init__(self, prefix: str):
        self.prefix = prefix
        self.redis_client = None
        redis_url = getattr(settings, "REDIS_URL", None)
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = aioredis.from_url(
                    redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
            except Exception as e:
                logger.error(f"Failed to initialize Redis client in cache context '{prefix}': {e}")
        
        self._local_cache = TTLLRUCache(maxsize=1000)

    def _get_key(self, key: str) -> str:
        return f"{self.prefix}:{key}"

    async def get(self, key: str) -> Optional[Any]:
        full_key = self._get_key(key)
        if self.redis_client:
            try:
                val = await self.redis_client.get(full_key)
                return json.loads(val) if val else None
            except Exception as e:
                logger.error(f"Redis get failed in '{self.prefix}': {e}")
        
        return self._local_cache.get(full_key)

    async def set(self, key: str, value: Any, ttl: int = 3600):
        full_key = self._get_key(key)
        if self.redis_client:
            try:
                await self.redis_client.set(
                    full_key,
                    json.dumps(value),
                    ex=ttl
                )
                return
            except Exception as e:
                logger.error(f"Redis set failed in '{self.prefix}': {e}")
        
        self._local_cache.set(full_key, value, ttl=ttl)

    async def delete(self, key: str):
        full_key = self._get_key(key)
        if self.redis_client:
            try:
                await self.redis_client.delete(full_key)
                return
            except Exception as e:
                logger.error(f"Redis delete failed in '{self.prefix}': {e}")
        
        self._local_cache.delete(full_key)