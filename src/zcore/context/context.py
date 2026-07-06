"""ZCore Thread and Coroutine Context Management.

This module provides thread-local and coroutine-safe state storage using Python's 
`contextvars` library. It tracks the current authenticated user identifier and any 
restricted data fields configured on the active execution context. It manages these 
parameters across asynchronous task boundaries to prevent concurrent state pollution.
"""

import uuid
from contextvars import ContextVar, Token
from typing import Generator, Union
from contextlib import contextmanager

# Safe context variables scoped to the current asynchronous execution context
_current_user_id: ContextVar[Union[uuid.UUID, None]] = ContextVar("user_id", default=None)
_restricted_fields: ContextVar[Union[frozenset[str], None]] = ContextVar("restricted_fields", default=None)


def set_current_user_id(user_id: Union[uuid.UUID, str, None]) -> Token[Union[uuid.UUID, None]]: 
    """Set the current authenticated user's identifier in the execution context.

    Converts string-based UUID parameters into formal `uuid.UUID` class instances 
    immediately to ensure downstream type integrity and avoid resolution errors.

    Args:
        user_id: The identifier to set in the context. Can be a pre-constructed 
            `uuid.UUID` instance, a valid UUID string, or None to clear the active context.

    Returns:
        A context token representing the previous state, used to restore context 
        boundaries later.

    Raises:
        ValueError: If a string-based parameter is not a valid UUID string representation.
        TypeError: If the parameter is not a `uuid.UUID` object, a string, or None.
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
    """Retrieve the current user identifier from the active execution context.

    Returns:
        The active user's UUID, or None if the current context is unauthenticated.
    """
    return _current_user_id.get()


def set_restricted_fields(
    fields: Union[set[str], list[str], frozenset[str], None]
) -> Token[Union[frozenset[str], None]]:
    """Configure the restricted data fields for the active execution context.

    Converts raw sequence parameters (lists or standard sets) into immutable `frozenset` 
    structures to enforce mutation-safe isolation and prevent accidental leaks.

    Args:
        fields: A collection of blocked field dot-paths, or None to clear active restrictions.

    Returns:
        A context token representing the previous state, used to restore context 
        boundaries later.
    """
    if fields is None:
        return _restricted_fields.set(None)
    
    # Store as frozenset to guarantee thread-safe and mutation-safe isolation
    frozen_fields = frozenset(fields)
    return _restricted_fields.set(frozen_fields)


def get_restricted_fields() -> frozenset[str]:
    """Retrieve the set of restricted fields configured on the active execution context.

    Returns:
        An immutable frozenset containing field dot-paths blocked from being loaded 
        by query builders or exposed by response projection utilities.
    """
    val = _restricted_fields.get()
    if val is None:
        return frozenset()
    return val


@contextmanager
def user_context(user_id: Union[uuid.UUID, str, None]) -> Generator[None, None, None]:
    """Context manager to safely bind and restore a user identifier.

    Args:
        user_id: The target identifier to set. Accepts UUID instances, string 
            representations, or None.

    Yields:
        None.
    """
    token = set_current_user_id(user_id)
    try:
        yield
    finally:
        _current_user_id.reset(token)


@contextmanager
def restricted_fields_context(
    fields: Union[set[str], list[str], frozenset[str], None]
) -> Generator[None, None, None]:
    """Context manager to safely bind and restore restricted fields.

    Args:
        fields: A collection of blocked field paths to bind to the active block.

    Yields:
        None.
    """
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
    """Compound context manager to cleanly coordinate both user and restricted field states.

    Designed to handle context setups and teardowns atomically during HTTP request lifecycles.

    Args:
        user_id: The target identifier to bind.
        fields: The restricted field path collection to bind.

    Yields:
        None.
    """
    user_token = set_current_user_id(user_id)
    fields_token = set_restricted_fields(fields)
    try:
        yield
    finally:
        _current_user_id.reset(user_token)
        _restricted_fields.reset(fields_token)