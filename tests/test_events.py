import asyncio
import time
import uuid
from typing import Any
import pytest

from zcore.kernel.events import EventDispatcher

@pytest.mark.anyio
@pytest.mark.parametrize("event_name", [f"evt_{uuid.uuid4().hex[:6]}" for _ in range(2)])
async def test_subscribe_and_unsubscribe(event_name: str) -> None:
    dispatcher = EventDispatcher()
    calls: list[str] = []

    def sync_handler() -> str:
        calls.append("sync")
        return "sync_val"

    async def async_handler() -> str:
        calls.append("async")
        return "async_val"

    dispatcher.subscribe(event_name, sync_handler)
    dispatcher.subscribe(event_name, async_handler)

    res = await dispatcher.dispatch(event_name)
    assert "sync" in calls
    assert "async" in calls
    assert set(res) == {"sync_val", "async_val"}

    calls.clear()
    dispatcher.unsubscribe(event_name, sync_handler)
    dispatcher.unsubscribe(event_name, async_handler)

    res2 = await dispatcher.dispatch(event_name)
    assert not calls
    assert res2 == []

@pytest.mark.anyio
@pytest.mark.parametrize("event_name", [f"perf_{uuid.uuid4().hex[:6]}"])
async def test_dispatch_sync_and_async(event_name: str) -> None:
    dispatcher = EventDispatcher()

    async def async_handler_1() -> float:
        await asyncio.sleep(0.05)
        return 1.0

    async def async_handler_2() -> float:
        await asyncio.sleep(0.05)
        return 2.0

    def sync_handler() -> float:
        return 3.0

    dispatcher.subscribe(event_name, async_handler_1)
    dispatcher.subscribe(event_name, async_handler_2)
    dispatcher.subscribe(event_name, sync_handler)

    start_time = time.perf_counter()
    results = await dispatcher.dispatch(event_name)
    elapsed = time.perf_counter() - start_time

    assert elapsed < 0.09
    assert set(results) == {1.0, 2.0, 3.0}

@pytest.mark.anyio
@pytest.mark.parametrize("event_name", [f"err_{uuid.uuid4().hex[:6]}"])
async def test_event_error_isolation(event_name: str) -> None:
    dispatcher = EventDispatcher()
    executed: list[str] = []

    def sync_error_handler() -> None:
        executed.append("sync_err")
        raise ValueError("Sync error")

    async def async_error_handler() -> None:
        executed.append("async_err")
        raise ValueError("Async error")

    def sync_ok_handler() -> str:
        executed.append("sync_ok")
        return "ok"

    async def async_ok_handler() -> str:
        executed.append("async_ok")
        return "async_ok_val"

    dispatcher.subscribe(event_name, sync_error_handler)
    dispatcher.subscribe(event_name, async_error_handler)
    dispatcher.subscribe(event_name, sync_ok_handler)
    dispatcher.subscribe(event_name, async_ok_handler)

    results = await dispatcher.dispatch(event_name)

    assert "sync_err" in executed
    assert "async_err" in executed
    assert "sync_ok" in executed
    assert "async_ok" in executed

    assert "ok" in results
    assert "async_ok_val" in results
    assert None in results