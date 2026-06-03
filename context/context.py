import uuid
from contextvars import ContextVar

_current_user_id: ContextVar[uuid.UUID | None] = ContextVar("user_id", default=None)
_restricted_fields: ContextVar[set[str] | None] = ContextVar("restricted_fields", default=None)

def set_current_user_id(user_id: uuid.UUID): 
    _current_user_id.set(user_id)
    
def get_current_user_id() -> uuid.UUID | None:
    return _current_user_id.get()

def set_restricted_fields(fields: set[str]):
    _restricted_fields.set(fields)

def get_restricted_fields() -> set[str]:
    val = _restricted_fields.get()
    if val is None:
        return set()
    return set(val)