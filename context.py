import uuid
from contextvars import ContextVar

_current_user_id: ContextVar[uuid.UUID | None] = ContextVar("user_id", default=None)

def set_current_user_id(user_id: uuid.UUID): 
    _current_user_id.set(user_id)
    
def get_current_user_id() -> uuid.UUID | None:
    return _current_user_id.get()