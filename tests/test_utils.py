import datetime
from decimal import Decimal
import uuid
from typing import Any, Type
import pytest

from zcore.exceptions.base import ValidationError
from zcore.utils.helpers import json_dumps, json_loads, slugify
from zcore.utils.validators import validate_json_schema

@pytest.mark.parametrize(
    "input_val, expected_output",
    [
        (
            uuid.UUID("12345678-1234-5678-1234-567812345678"),
            '"12345678-1234-5678-1234-567812345678"'
        ),
        (
            datetime.datetime(2026, 7, 2, 10, 0, 0),
            '"2026-07-02T10:00:00"'
        ),
        (
            datetime.date(2026, 7, 2),
            '"2026-07-02"'
        ),
        (
            datetime.time(10, 0, 0),
            '"10:00:00"'
        ),
        (
            Decimal("123.45"),
            "123.45"
        ),
        (
            {"user_id": uuid.UUID("12345678-1234-5678-1234-567812345678"), "balance": Decimal("9.99")},
            '{"user_id": "12345678-1234-5678-1234-567812345678", "balance": 9.99}'
        )
    ]
)
def test_custom_json_encoder(input_val: Any, expected_output: str) -> None:
    serialized = json_dumps(input_val)
    assert json_loads(serialized) == json_loads(expected_output)

@pytest.mark.parametrize(
    "text, expected_slug",
    [
        ("Hello World!", "hello-world"),
        ("  SpAcE  and  _underscores_  ", "space-and-underscores"),
        ("Some - text - here!", "some-text-here"),
        ("---leading-and-trailing---", "leading-and-trailing"),
        ("special#@$chars%^&", "specialchars"),
    ]
)
def test_slugify_logic(text: str, expected_slug: str) -> None:
    assert slugify(text) == expected_slug

@pytest.mark.parametrize(
    "data, schema, should_pass, expected_error_msg",
    [
        (
            {"type": "object", "properties": {"id": {"type": "integer"}}},
            None,
            True,
            ""
        ),
        (
            {"type": "invalid_type_name_here"},
            None,
            False,
            "Internal System Error: The defined schema is corrupted or invalid."
        ),
        (
            {"id": 42, "name": "ZCore"},
            {"type": "object", "properties": {"id": {"type": "integer"}, "name": {"type": "string"}}, "required": ["id"]},
            True,
            ""
        ),
        (
            {"id": "not_an_integer", "name": "ZCore"},
            {"type": "object", "properties": {"id": {"type": "integer"}}},
            False,
            "JSON Schema validation failed"
        ),
        (
            None,
            {"type": "object"},
            True,
            ""
        ),
    ]
)
def test_validate_json_schema(
    data: Any,
    schema: dict[str, Any] | None,
    should_pass: bool,
    expected_error_msg: str
) -> None:
    if should_pass:
        validate_json_schema(data, schema)
    else:
        with pytest.raises(ValidationError) as exc_info:
            validate_json_schema(data, schema)
        assert expected_error_msg in str(exc_info.value)