from sqlalchemy import event
from sqlalchemy.orm import Session

from app.core.plugin.hooks import hook_registry, DBEvent

@event.listens_for(Session, "before_flush")
def dispatch_before_flush(session, flush_context, instances):
    for handler in hook_registry.get_db_handlers(DBEvent.BEFORE_FLUSH):
        handler(session)