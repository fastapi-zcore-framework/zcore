from typing import Any, Type
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
import pytest

from zcore.exceptions.base import (
    AppException,
    AuthError,
    DuplicateEntity,
    EntityNotFound,
    ForbiddenError,
    ValidationError,
)
from zcore.exceptions.handlers import app_exception_handler

@pytest.mark.parametrize(
    "exc_class, status_code, message, payload",
    [
        (EntityNotFound, 404, "Not Found", {"id": "123"}),
        (DuplicateEntity, 409, "Already Exists", {"key": "unique"}),
        (AuthError, 401, "No Authentication", None),
        (ForbiddenError, 403, "Access Blocked", {"role": "guest"}),
        (ValidationError, 400, "Validation Failed", {"field": "email"}),
        (AppException, 500, "Internal Server Error", None),
    ]
)
def test_exception_status_codes(
    exc_class: Type[AppException],
    status_code: int,
    message: str,
    payload: dict[str, Any] | None
) -> None:
    exc = exc_class(message, payload=payload)
    assert exc.status_code == status_code
    assert exc.message == message
    assert exc.payload == payload

@pytest.mark.anyio
@pytest.mark.parametrize(
    "exc_to_raise, expected_status, expected_msg, expected_meta_payload",
    [
        (EntityNotFound("Item missing", {"id": "abc"}), 404, "Item missing", {"id": "abc"}),
        (ValidationError("Bad request", {"reason": "missing field"}), 400, "Bad request", {"reason": "missing field"}),
        (AuthError("Unauthorized session", None), 401, "Unauthorized session", None),
    ]
)
async def test_app_exception_handler_middleware(
    exc_to_raise: AppException,
    expected_status: int,
    expected_msg: str,
    expected_meta_payload: dict[str, Any] | None
) -> None:
    app = FastAPI()
    app.add_exception_handler(AppException, app_exception_handler)

    @app.get("/trigger")
    def trigger_error() -> None:
        raise exc_to_raise

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/trigger")
        assert response.status_code == expected_status
        
        body = response.json()
        assert body["success"] is False
        assert body["message"] == expected_msg
        assert body["data"] is None
        assert body["meta"]["error_type"] == exc_to_raise.__class__.__name__
        assert body["meta"]["payload"] == expected_meta_payload