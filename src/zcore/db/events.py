import structlog
from typing import Any
from zcore.kernel.events import EventDispatcher

logger = structlog.get_logger()

_global_dispatcher: EventDispatcher | None = None

def register_db_event_dispatcher(dispatcher: EventDispatcher) -> None:
    global _global_dispatcher
    _global_dispatcher = dispatcher

async def dispatch_db_event(event_name: str, payload: Any) -> None:
    """
    Safely dispatches database life-cycle events within the async event loop.
    No synchronous greenlet-blocking operations allowed here.
    """
    if not _global_dispatcher:
        return
    try:
        await _global_dispatcher.dispatch(event_name, payload)
    except Exception as e:
        logger.error(f"Failed to dispatch database event '{event_name}': {e}", exc_info=True)