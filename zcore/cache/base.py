import logging
from typing import Any, Optional, TypeVar, Generic
from zcore.cache.ttllru_cache import TTLLRUCache
from zcore.utils.helpers import json_dumps, json_loads

T = TypeVar("T")
logger = logging.getLogger(__name__)

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

_shared_redis_client: Any = None

def init_cache(redis_url: Optional[str] = None, **kwargs: Any) -> None:
    global _shared_redis_client
    if REDIS_AVAILABLE and redis_url:
        try:
            _shared_redis_client = aioredis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Failed to initialize shared Redis client: {e}")

class BaseCache(Generic[T]):
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        self._local_cache = TTLLRUCache(maxsize=1000)

    @property
    def redis_client(self) -> Any:
        return _shared_redis_client

    def _get_key(self, key: str) -> str:
        return f"{self.prefix}:{key}"

    async def get(self, key: str) -> Optional[T]:
        full_key = self._get_key(key)
        client = self.redis_client
        if client:
            try:
                val = await client.get(full_key)
                return json_loads(val) if val else None
            except Exception as e:
                logger.error(f"Redis get failed in '{self.prefix}': {e}")
        
        return self._local_cache.get(full_key)

    async def set(self, key: str, value: T, ttl: int = 3600) -> None:
        full_key = self._get_key(key)
        client = self.redis_client
        if client:
            try:
                await client.set(
                    full_key,
                    json_dumps(value),
                    ex=ttl
                )
                return
            except Exception as e:
                logger.error(f"Redis set failed in '{self.prefix}': {e}")
        
        self._local_cache.set(full_key, value, ttl=ttl)

    async def delete(self, key: str) -> None:
        full_key = self._get_key(key)
        client = self.redis_client
        if client:
            try:
                await client.delete(full_key)
                return
            except Exception as e:
                logger.error(f"Redis delete failed in '{self.prefix}': {e}")
        
        self._local_cache.delete(full_key)