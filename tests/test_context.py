import uuid
from typing import Any, Type
import pytest

from zcore.context.context import (
    _current_user_id,
    _restricted_fields,
    get_current_user_id,
    get_restricted_fields,
    request_context,
    restricted_fields_context,
    set_current_user_id,
    set_restricted_fields,
    user_context,
)

@pytest.mark.parametrize(
    "user_id_input, expected_output, expected_exception",
    [
        ("12345678-1234-5678-1234-567812345678", uuid.UUID("12345678-1234-5678-1234-567812345678"), None),
        (uuid.UUID("12345678-1234-5678-1234-567812345678"), uuid.UUID("12345678-1234-5678-1234-567812345678"), None),
        (None, None, None),
        ("invalid-uuid-string", None, ValueError),
        (12345, None, TypeError),
    ]
)
def test_set_current_user_id_validation(
    user_id_input: Any,
    expected_output: uuid.UUID | None,
    expected_exception: Type[Exception] | None
) -> None:
    if expected_exception:
        with pytest.raises(expected_exception):
            set_current_user_id(user_id_input)
    else:
        token = set_current_user_id(user_id_input)
        assert get_current_user_id() == expected_output
        _current_user_id.reset(token)

@pytest.mark.parametrize(
    "fields_input, expected_output",
    [
        ({"password", "credit_card"}, frozenset({"password", "credit_card"})),
        (["password", "credit_card"], frozenset({"password", "credit_card"})),
        (frozenset({"password"}), frozenset({"password"})),
        (None, frozenset()),
    ]
)
def test_set_restricted_fields_immutability(
    fields_input: Any,
    expected_output: frozenset[str]
) -> None:
    token = set_restricted_fields(fields_input)
    retrieved = get_restricted_fields()
    assert retrieved == expected_output
    assert isinstance(retrieved, frozenset)
    assert not hasattr(retrieved, "add")
    assert not hasattr(retrieved, "remove")
    _restricted_fields.reset(token)

def test_context_managers_cleanup() -> None:
    initial_user = uuid.uuid4()
    initial_fields = {"email"}
    
    set_current_user_id(initial_user)
    set_restricted_fields(initial_fields)
    
    new_user = uuid.uuid4()
    with pytest.raises(RuntimeError):
        with user_context(new_user):
            assert get_current_user_id() == new_user
            raise RuntimeError("Error inside user_context")
    assert get_current_user_id() == initial_user
    
    new_fields = {"password"}
    with pytest.raises(RuntimeError):
        with restricted_fields_context(new_fields):
            assert get_restricted_fields() == frozenset(new_fields)
            raise RuntimeError("Error inside restricted_fields_context")
    assert get_restricted_fields() == frozenset(initial_fields)

    with pytest.raises(RuntimeError):
        with request_context(new_user, new_fields):
            assert get_current_user_id() == new_user
            assert get_restricted_fields() == frozenset(new_fields)
            raise RuntimeError("Error inside request_context")
    assert get_current_user_id() == initial_user
    assert get_restricted_fields() == frozenset(initial_fields)