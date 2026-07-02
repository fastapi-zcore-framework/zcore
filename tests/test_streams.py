import asyncio
import uuid
from typing import Any
from unittest.mock import MagicMock
import pytest

from zcore.web.streams import StreamManager

@pytest.fixture(autouse=True)
def bypass_redis_pubsub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("zcore.web.streams._stream_redis_client", None)

@pytest.mark.anyio
@pytest.mark.parametrize("num_subscribers", [1, 3])
async def test_stream_pubsub_lifecycle(num_subscribers: int) -> None:
    manager = StreamManager()
    user_id = uuid.uuid4()
    
    assert len(manager.users_queues) == 0
    assert manager._pubsub_task is None

    queues: list[asyncio.Queue[Any]] = []
    for _ in range(num_subscribers):
        q = await manager.subscribe(user_id)
        queues.append(q)

    assert len(manager.users_queues) == 1
    assert len(manager.users_queues[user_id]) == num_subscribers
    assert manager._pubsub_task is None

    payload = {"message_id": str(uuid.uuid4()), "event": "test_signal"}
    await manager.publish(user_id, payload)

    for q in queues:
        received = await asyncio.wait_for(q.get(), timeout=1.0)
        assert received == payload

    for q in queues:
        await manager.unsubscribe(user_id, q)

    assert len(manager.users_queues) == 0
    assert manager._pubsub_task is None

@pytest.mark.anyio
@pytest.mark.parametrize(
    "total_queues, overflow_index",
    [
        (2, 0),
        (3, 1),
    ]
)
async def test_stream_queue_overflow(total_queues: int, overflow_index: int) -> None:
    manager = StreamManager()
    user_id = uuid.uuid4()
    
    queues: list[asyncio.Queue[Any]] = []
    for _ in range(total_queues):
        q = await manager.subscribe(user_id)
        queues.append(q)

    overflow_queue = queues[overflow_index]
    overflow_queue.put_nowait = MagicMock(side_effect=asyncio.QueueFull)

    payload = {"alert": "system_overload"}
    await manager.publish(user_id, payload)

    assert overflow_queue not in manager.users_queues[user_id]
    assert len(manager.users_queues[user_id]) == total_queues - 1

    for i, q in enumerate(queues):
        if i != overflow_index:
            received = await asyncio.wait_for(q.get(), timeout=1.0)
            assert received == payload

    for q in list(manager.users_queues.get(user_id, [])):
        await manager.unsubscribe(user_id, q)