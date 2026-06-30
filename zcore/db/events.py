import asyncio
import logging
from typing import Any
from sqlalchemy import event
from sqlalchemy.orm import Session

from zcore.kernel.events import EventDispatcher

logger = logging.getLogger(__name__)
_global_dispatcher: EventDispatcher | None = None

def register_db_event_dispatcher(dispatcher: EventDispatcher) -> None:
    global _global_dispatcher
    _global_dispatcher = dispatcher

def _safe_async_dispatch(event_name: str, *args: Any, **kwargs: Any) -> None:
    if not _global_dispatcher:
        return
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            coro = _global_dispatcher.dispatch(event_name, *args, **kwargs)
            task = loop.create_task(coro)
            
            def _handle_exception(t: asyncio.Task) -> None:
                try:
                    t.result()
                except Exception as e:
                    logger.error(f"Async database event listener failed: {e}")
                    
            task.add_done_callback(_handle_exception)
    except RuntimeError:
        pass

@event.listens_for(Session, "before_flush")
def dispatch_before_flush(session: Any, flush_context: Any, instances: Any) -> None:
    _safe_async_dispatch("db:before_flush", session)

@event.listens_for(Session, "after_commit")
def dispatch_after_commit(session: Any) -> None:
    _safe_async_dispatch("db:after_commit", session)