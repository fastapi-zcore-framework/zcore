import uuid
import asyncio
import json
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

class StreamManager:
    def __init__(self):
        self.users_queues: dict[uuid.UUID, list[asyncio.Queue]] = {}
        self.redis_client = None
        self._pubsub_task = None
        self._pubsub = None

        redis_url = getattr(settings, "REDIS_URL", None)
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = aioredis.from_url(
                    redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
            except Exception as e:
                logger.error(f"Failed to initialize Redis for StreamManager: {e}")

    async def start_listening(self):
        if not self.redis_client:
            return
        
        try:
            self._pubsub = self.redis_client.pubsub()
            await self._pubsub.psubscribe("stream:user:*")
            self._pubsub_task = asyncio.create_task(self._listen_to_redis())
        except Exception as e:
            logger.error(f"Failed to subscribe to Redis PubSub: {e}")

    async def _listen_to_redis(self):
        try:
            async for message in self._pubsub.listen():
                if message["type"] == "pmessage":
                    channel = message["channel"]
                    user_id_str = channel.split(":")[-1]
                    try:
                        user_id = uuid.UUID(user_id_str)
                    except ValueError:
                        continue
                    
                    data = json.loads(message["data"])
                    await self._local_publish(user_id, data)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in Redis PubSub stream listener: {e}")

    async def subscribe(self, user_id: uuid.UUID) -> asyncio.Queue:
        queue = asyncio.Queue(maxsize=100)
        if user_id not in self.users_queues:
            self.users_queues[user_id] = []
            if self.redis_client and (self._pubsub_task is None or self._pubsub_task.done()):
                await self.start_listening()
                
        self.users_queues[user_id].append(queue)
        return queue

    async def unsubscribe(self, user_id: uuid.UUID, queue: asyncio.Queue):
        if user_id in self.users_queues:
            self.users_queues[user_id].remove(queue)
            
            if not self.users_queues[user_id]:
                del self.users_queues[user_id]

    async def publish(self, user_id: uuid.UUID, data: dict):
        if self.redis_client:
            try:
                await self.redis_client.publish(
                    f"stream:user:{user_id}",
                    json.dumps(data)
                )
                return
            except Exception as e:
                logger.error(f"Redis publish failed: {e}")
        
        await self._local_publish(user_id, data)

    async def _local_publish(self, user_id: uuid.UUID, data: dict):
        queues = self.users_queues.get(user_id)
        if not queues:
            return
        
        for queue in list(queues):
            try:
                queue.put_nowait(data)
            except asyncio.QueueFull:
                await self.unsubscribe(user_id, queue)
            
stream_manager = StreamManager()