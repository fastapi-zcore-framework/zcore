import asyncio
from typing import Any
from sqlalchemy import event
from sqlalchemy.orm import Session

from zcore.kernel.events import EventDispatcher

_global_dispatcher: EventDispatcher | None = None

def register_db_event_dispatcher(dispatcher: EventDispatcher) -> None:
    global _global_dispatcher
    _global_dispatcher = dispatcher

@event.listens_for(Session, "before_flush")
def dispatch_before_flush(session: Any, flush_context: Any, instances: Any) -> None:
    if _global_dispatcher:
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                loop.create_task(_global_dispatcher.dispatch("db:before_flush", session))
        except RuntimeError:
            pass

@event.listens_for(Session, "after_commit")
def dispatch_after_commit(session: Any) -> None:
    if _global_dispatcher:
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                loop.create_task(_global_dispatcher.dispatch("db:after_commit", session))
        except RuntimeError:
            pass