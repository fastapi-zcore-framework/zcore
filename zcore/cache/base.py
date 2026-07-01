import structlog
import asyncio
from typing import Any, Optional, TypeVar, Generic, Type, Union
from pydantic import BaseModel

from zcore.cache.ttllru_cache import TTLLRUCache
from zcore.utils.helpers import json_dumps, json_loads

T = TypeVar("T")
logger = structlog.get_logger()

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

_shared_redis_client: Optional[Any] = None
_eviction_task: Optional[asyncio.Task] = None

def init_cache(redis_url: Optional[str] = None, **kwargs: Any) -> None:
    """Initializes the shared Redis client and spawns the background memory eviction loop."""
    global _shared_redis_client, _eviction_task
    
    if REDIS_AVAILABLE and redis_url:
        try:
            _shared_redis_client = aioredis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                **kwargs
            )
            logger.info("Shared Redis cache client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize shared Redis client: {e}")
            
    if _eviction_task is None or _eviction_task.done():
        _eviction_task = asyncio.create_task(_start_eviction_loop(interval=60))

async def _start_eviction_loop(interval: int = 60) -> None:
    """Async background worker loop that periodically evicts expired entries from TTLLRUCache."""
    while True:
        try:
            await asyncio.sleep(interval)
            TTLLRUCache.evict_all_expired()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in cache memory eviction loop: {e}")

async def close_cache() -> None:
    global _shared_redis_client, _eviction_task
    
    if _eviction_task and not _eviction_task.done():
        _eviction_task.cancel()
        _eviction_task = None
        logger.info("Cache memory eviction loop stopped.")
        
    if _shared_redis_client:
        try:
            await _shared_redis_client.close()
            _shared_redis_client = None
            logger.info("Shared Redis cache connection closed successfully.")
        except Exception as e:
            logger.error(f"Failed to cleanly close Redis cache: {e}")

class BaseCache(Generic[T]):
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        self._local_cache = TTLLRUCache(maxsize=1000)

    @property
    def redis_client(self) -> Any:
        return _shared_redis_client

    def _get_key(self, key: str) -> str:
        return f"{self.prefix}:{key}"

    async def get(self, key: str, target_type: Optional[Type[BaseModel]] = None) -> Optional[Union[T, BaseModel, Any]]:
        """
        Retrieves an item from the cache.
        If target_type is provided as a Pydantic model class, the cached JSON payload
        is automatically deserialized and validated.
        """
        full_key = self._get_key(key)
        client = self.redis_client
        raw_val = None
        
        if client:
            try:
                raw_val = await client.get(full_key)
            except Exception as e:
                logger.error(f"Redis get failed in '{self.prefix}': {e}")
                
        if raw_val is None:
            raw_val = self._local_cache.get(full_key)
            
        if raw_val is None:
            return None
            
        try:
            # Parse the string/bytes to JSON primitives
            # If retrieved from local cache, it might already be parsed, check type safely
            parsed_data = json_loads(raw_val) if isinstance(raw_val, (str, bytes)) else raw_val
            
            if target_type and issubclass(target_type, BaseModel):
                return target_type.model_validate(parsed_data)
                
            return parsed_data
        except Exception as e:
            logger.error(f"Failed to deserialize cache key '{full_key}': {e}")
            return None

    async def set(self, key: str, value: T, ttl: int = 3600) -> None:
        full_key = self._get_key(key)
        client = self.redis_client
        
        # Serialize the value securely
        serialized_val = json_dumps(value) if not isinstance(value, (str, int, float, bool)) else value
        
        if client:
            try:
                await client.set(
                    full_key,
                    serialized_val,
                    ex=ttl
                )
                return
            except Exception as e:
                logger.error(f"Redis set failed in '{self.prefix}': {e}")
        
        self._local_cache.set(full_key, serialized_val, ttl=ttl)

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