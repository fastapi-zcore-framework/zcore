import uuid
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import inspect
from sqlalchemy.orm import attributes

from app.core.context import get_current_user_id

def to_json_safe(value):
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, list):
        return [to_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {k: to_json_safe(v) for k, v in value.items()}
    return value

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
            val_added = history.added[0] if history.added else None
            payload[column] = to_json_safe(val_added)
            # values that are being replaced
            val_deleted = history.deleted[0] if history.deleted else None
            before_state[column] = to_json_safe(val_deleted)
            
    return payload, before_state

def handle_outbox_events(session, flush_context, instances):
    from app.core.messaging.models import OutboxEvent
    user_id = get_current_user_id()
    
    for obj in session.new.union(session.dirty).union(session.deleted):
        if isinstance(obj, OutboxEvent):
            continue
        
        mapper = inspect(obj).mapper
        pk_column = mapper.primary_key[0].name
        
        current_pk_value = getattr(obj, pk_column)
        if current_pk_value is None:
            new_id = uuid.uuid4()
            setattr(obj, pk_column, new_id)
            current_pk_value = new_id
        
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
            aggregate_id=current_pk_value,
            event_type=f"{obj.__tablename__}:{action}",
            payload=payload,
            before_state=before_state,
            user_id=user_id
        )
        
        session.add(new_event)