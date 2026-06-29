import uuid
from contextvars import ContextVar, Token
from typing import Optional, Generator, set
from contextlib import contextmanager

_current_user_id: ContextVar[Optional[uuid.UUID]] = ContextVar("user_id", default=None)
_restricted_fields: ContextVar[Optional[set[str]]] = ContextVar("restricted_fields", default=None)

def set_current_user_id(user_id: Optional[uuid.UUID]) -> Token[Optional[uuid.UUID]]: 
    return _current_user_id.set(user_id)
    
def get_current_user_id() -> Optional[uuid.UUID]:
    return _current_user_id.get()

def set_restricted_fields(fields: Optional[set[str]]) -> Token[Optional[set[str]]]:
    return _restricted_fields.set(fields)

def get_restricted_fields() -> set[str]:
    val = _restricted_fields.get()
    if val is None:
        return set()
    return set(val)

@contextmanager
def user_context(user_id: Optional[uuid.UUID]) -> Generator[None, None, None]:
    token = _current_user_id.set(user_id)
    try:
        yield
    finally:
        _current_user_id.reset(token)

@contextmanager
def restricted_fields_context(fields: Optional[set[str]]) -> Generator[None, None, None]:
    token = _restricted_fields.set(fields)
    try:
        yield
    finally:
        _restricted_fields.reset(token)

@contextmanager
def request_context(user_id: Optional[uuid.UUID], fields: Optional[set[str]]) -> Generator[None, None, None]:
    user_token = _current_user_id.set(user_id)
    fields_token = _restricted_fields.set(fields)
    try:
        yield
    finally:
        _current_user_id.reset(user_token)
        _restricted_fields.reset(fields_token)