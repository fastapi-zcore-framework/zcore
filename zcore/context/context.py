import uuid
from contextvars import ContextVar, Token
from typing import Generator, Union
from contextlib import contextmanager

# Clean and secure context variables using Python modern typing
_current_user_id: ContextVar[Union[uuid.UUID, None]] = ContextVar("user_id", default=None)
_restricted_fields: ContextVar[Union[frozenset[str], None]] = ContextVar("restricted_fields", default=None)

def set_current_user_id(user_id: Union[uuid.UUID, str, None]) -> Token[Union[uuid.UUID, None]]: 
    """
    Sets the current authenticated user's ID with robust validation.
    Converts string UUIDs to formal uuid.UUID objects immediately to prevent downstream type errors.
    """
    if user_id is None:
        return _current_user_id.set(None)
        
    if isinstance(user_id, str):
        try:
            validated_id = uuid.UUID(user_id)
        except ValueError as e:
            raise ValueError(f"Invalid UUID string provided to context: '{user_id}'") from e
    elif isinstance(user_id, uuid.UUID):
        validated_id = user_id
    else:
        raise TypeError("user_id must be an instance of uuid.UUID, a valid UUID string, or None")

    return _current_user_id.set(validated_id)
    
def get_current_user_id() -> Union[uuid.UUID, None]:
    """Retrieves the current user ID from the context."""
    return _current_user_id.get()

def set_restricted_fields(fields: Union[set[str], list[str], frozenset[str], None]) -> Token[Union[frozenset[str], None]]:
    """
    Sets the restricted/hidden fields for the current request.
    Forces immutability by converting the input to a frozenset to prevent mutation leaks.
    """
    if fields is None:
        return _restricted_fields.set(None)
    
    # Store as frozenset to guarantee thread-safe and mutation-safe isolation
    frozen_fields = frozenset(fields)
    return _restricted_fields.set(frozen_fields)

def get_restricted_fields() -> frozenset[str]:
    """
    Retrieves the restricted fields as an immutable frozenset.
    Safe to pass around without risk of accidental mutation.
    """
    val = _restricted_fields.get()
    if val is None:
        return frozenset()
    return val

@contextmanager
def user_context(user_id: Union[uuid.UUID, str, None]) -> Generator[None, None, None]:
    """Context manager for safely setting and restoring the user context."""
    token = set_current_user_id(user_id)
    try:
        yield
    finally:
        _current_user_id.reset(token)

@contextmanager
def restricted_fields_context(fields: Union[set[str], list[str], frozenset[str], None]) -> Generator[None, None, None]:
    """Context manager for safely setting and restoring restricted fields."""
    token = set_restricted_fields(fields)
    try:
        yield
    finally:
        _restricted_fields.reset(token)

@contextmanager
def request_context(
    user_id: Union[uuid.UUID, str, None], 
    fields: Union[set[str], list[str], frozenset[str], None]
) -> Generator[None, None, None]:
    """Compound context manager to cleanly handle entire HTTP request contexts at once."""
    user_token = set_current_user_id(user_id)
    fields_token = set_restricted_fields(fields)
    try:
        yield
    finally:
        _current_user_id.reset(user_token)
        _restricted_fields.reset(fields_token)