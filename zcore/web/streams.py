import uuid
import asyncio
import logging
from typing import Any, Optional
from zcore.utils.helpers import json_dumps, json_loads

logger = logging.getLogger(__name__)

_stream_redis_client: Any = None

def init_stream_redis(client: Any) -> None:
    global _stream_redis_client
    _stream_redis_client = client

class StreamManager:
    def __init__(self) -> None:
        self.users_queues: dict[uuid.UUID, list[asyncio.Queue[Any]]] = {}
        self._pubsub_task: Optional[asyncio.Task[None]] = None
        self._pubsub: Any = None
        self._lock = asyncio.Lock()

    @property
    def redis_client(self) -> Any:
        return _stream_redis_client

    async def start_listening(self) -> None:
        client = self.redis_client
        if not client:
            return
        
        try:
            self._pubsub = client.pubsub()
            await self._pubsub.psubscribe("stream:user:*")
            self._pubsub_task = asyncio.create_task(self._listen_to_redis())
        except Exception as e:
            logger.error(f"Failed to subscribe to Redis PubSub: {e}")

    async def _listen_to_redis(self) -> None:
        try:
            async for message in self._pubsub.listen():
                if message["type"] == "pmessage":
                    channel = message["channel"]
                    user_id_str = channel.split(":")[-1]
                    try:
                        user_id = uuid.UUID(user_id_str)
                    except ValueError:
                        continue
                    
                    data = json_loads(message["data"])
                    await self._local_publish(user_id, data)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in Redis PubSub stream listener: {e}")

    async def subscribe(self, user_id: uuid.UUID) -> asyncio.Queue[Any]:
        queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=100)
        async with self._lock:
            if user_id not in self.users_queues:
                self.users_queues[user_id] = []
                client = self.redis_client
                if client and (self._pubsub_task is None or self._pubsub_task.done()):
                    await self.start_listening()
                    
            self.users_queues[user_id].append(queue)
        return queue

    def unsubscribe(self, user_id: uuid.UUID, queue: asyncio.Queue[Any]) -> None:
        if user_id in self.users_queues:
            if queue in self.users_queues[user_id]:
                self.users_queues[user_id].remove(queue)
            
            if not self.users_queues[user_id]:
                del self.users_queues[user_id]

        if not self.users_queues and self._pubsub_task and not self._pubsub_task.done():
            self._pubsub_task.cancel()
            self._pubsub_task = None

    async def publish(self, user_id: uuid.UUID, data: dict[str, Any]) -> None:
        client = self.redis_client
        if client:
            try:
                await client.publish(
                    f"stream:user:{user_id}",
                    json_dumps(data)
                )
                return
            except Exception as e:
                logger.error(f"Redis publish failed: {e}")
        
        await self._local_publish(user_id, data)

    async def _local_publish(self, user_id: uuid.UUID, data: dict[str, Any]) -> None:
        queues = self.users_queues.get(user_id)
        if not queues:
            return
        
        for queue in list(queues):
            try:
                queue.put_nowait(data)
            except asyncio.QueueFull:
                self.unsubscribe(user_id, queue)

stream_manager = StreamManager()