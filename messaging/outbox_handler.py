from sqlalchemy import inspect
from sqlalchemy.orm import attributes

from app.core.context import get_current_user_id

def extract_changes(obj):
    payload = {}
    before_state = {}
    
    # 1. Get the mapper to see all columns
    for column in obj.__mapper__.columns.keys():
        if column == "password_hash":
            continue
        
        # 2. Get the history of this specific column
        history = attributes.get_history(obj, column)
        
        if history.has_changes():
            # values that are being added
            payload[column] = history.added[0] if history.added else None
            # values that are being replaced
            before_state[column] = history.deleted[0] if history.deleted else None
            
    return payload, before_state

def handle_outbox_events(session, flush_context, instances):
    from app.core.messaging.models import OutboxEvent
    user_id = get_current_user_id()
    
    for obj in session.new.union(session.dirty).union(session.deleted):
        if isinstance(obj, OutboxEvent):
            continue
        
        state = inspect(obj)
        
        if state.pending:
            action = "create"
        elif state.deleted:
            action = "delete"
        elif state.persistent and state.modified:
            action = "update"
        else:
            continue
        
        payload, before_state = extract_changes(obj)
        
        new_event = OutboxEvent(
            aggregate_type=obj.__tablename__,
            aggregate_id=obj.id,
            event_type=f"{obj.__tablename__}:{action}",
            payload=payload,
            before_state=before_state,
            user_id=user_id
        )
        
        session.add(new_event)