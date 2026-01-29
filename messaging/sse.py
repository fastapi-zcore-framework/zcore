import uuid
import asyncio

class StreamManager:
    def __init__(self):
        self.users_queues: dict[uuid.UUID, list[asyncio.Queue]] = {}

    async def subscribe(self, user_id: uuid.UUID) -> asyncio.Queue:
        queue = asyncio.Queue(maxsize=100)
        if user_id not in self.users_queues:
            self.users_queues[user_id] = []
        self.users_queues[user_id].append(queue)
        return queue

    async def unsubscribe(self, user_id: uuid.UUID, queue: asyncio.Queue):
        if user_id in self.users_queues:
            self.users_queues[user_id].remove(queue)
            
            if not self.users_queues[user_id]:
                del self.users_queues[user_id]

    async def publish(self, user_id: uuid.UUID, data: dict):
        queues = self.users_queues.get(user_id)
        
        if not queues:
            return
        
        for queue in queues:
            try:
                queue.put_nowait(data)
            except asyncio.QueueFull:
                pass
            