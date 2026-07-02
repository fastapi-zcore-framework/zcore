import inspect
import asyncio
import structlog
from collections import defaultdict
from typing import Callable, Any, Coroutine, TypeVar

logger = structlog.getLogger("zcore.events")

T = TypeVar("T")
EventHandler = Callable[..., Coroutine[Any, Any, Any] | Any]

class EventDispatcher:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        self._subscribers[event_name].append(handler)

    def unsubscribe(self, event_name: str, handler: EventHandler) -> None:
        if event_name in self._subscribers and handler in self._subscribers[event_name]:
            self._subscribers[event_name].remove(handler)

    async def dispatch(self, event_name: str, *args: Any, **kwargs: Any) -> list[Any]:
        handlers = self._subscribers.get(event_name, [])
        if not handlers:
            return []

        async_tasks = []
        sync_results = []

        for handler in handlers:
            try:
                if inspect.iscoroutinefunction(handler):
                    # Prepare for concurrent execution
                    async_tasks.append(handler(*args, **kwargs))
                else:
                    sync_results.append(handler(*args, **kwargs))
            except Exception as e:
                logger.error(f"Error preparing event handler {handler.__name__} for event '{event_name}': {e}")

        # Run async event tasks concurrently to prevent sequential bottlenecking
        async_results = []
        if async_tasks:
            results = await asyncio.gather(*async_tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, Exception):
                    logger.error(f"Unhandled exception in async event listener for event '{event_name}': {res}")
                    async_results.append(None)
                else:
                    async_results.append(res)

        return sync_results + async_results