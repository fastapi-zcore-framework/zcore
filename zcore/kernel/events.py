import inspect
from collections import defaultdict
from typing import Callable, Any, Coroutine, TypeVar

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
        results = []
        for handler in handlers:
            if inspect.iscoroutinefunction(handler):
                results.append(await handler(*args, **kwargs))
            else:
                results.append(handler(*args, **kwargs))
        return results