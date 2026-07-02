import uuid
from typing import Any, Type
from unittest.mock import MagicMock
from fastapi import FastAPI, APIRouter
from httpx import ASGITransport, AsyncClient
import pytest
from pydantic import BaseModel

from zcore.kernel.di import container
from zcore.web.api_router import ZCoreJSONResponse
from zcore.web.base_router import BaseRouter, RouteKey
from zcore.web.middleware import RequestLogMiddleware
from zcore.web.projection import ResponseProjector

class DummyModel:
    @classmethod
    def actions(cls) -> Any:
        mock_actions = MagicMock()
        mock_actions.CREATE = "dummy:create"
        mock_actions.VIEW = "dummy:view"
        mock_actions.LISTVIEW = "dummy:listview"
        mock_actions.UPDATE = "dummy:update"
        mock_actions.DELETE = "dummy:delete"
        return mock_actions

class DummyCreate(BaseModel):
    name: str

class DummyUpdate(BaseModel):
    name: str

class DummyOut(BaseModel):
    id: str
    name: str
    password: str

@pytest.mark.parametrize(
    "router_attrs, expected_error_msg",
    [
        (
            {"service": None},
            "Service class must be defined"
        ),
        (
            {"service": MagicMock(), "create_schema": None, "exclude": set()},
            "POST route is enabled"
        ),
        (
            {"service": MagicMock(), "create_schema": DummyCreate, "update_schema": None, "exclude": set()},
            "UPDATE/PATCH route is enabled"
        ),
        (
            {
                "service": MagicMock(),
                "create_schema": DummyCreate,
                "update_schema": DummyUpdate,
                "model": None,
                "DEFAULT_PERMISSIONS": "AUTO",
            },
            "Model class must be defined"
        ),
    ]
)
def test_router_auto_scaffolding_validation_errors(router_attrs: dict[str, Any], expected_error_msg: str) -> None:
    attrs = {
        "model": DummyModel,
        "create_schema": DummyCreate,
        "update_schema": DummyUpdate,
        "schema_out": DummyOut,
    }
    attrs.update(router_attrs)
    
    router_cls = type("TestRouter", (BaseRouter,), attrs)
    
    with pytest.raises(ValueError) as exc_info:
        router_cls()
    assert expected_error_msg in str(exc_info.value)

class TargetService:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    async def get(self, id: uuid.UUID) -> DummyOut:
        return DummyOut(id=str(id), name=self.payload["name"], password=self.payload["password"])

    async def get_list(self, pagination: Any = None) -> list[Any]:
        return []

@pytest.mark.anyio
@pytest.mark.parametrize(
    "restricted_fields, payload_in, expected_payload_out, expected_vary",
    [
        (
            {"password", "resource.password"},
            {"id": "1", "name": "UserA", "password": "hash"},
            {"id": "1", "name": "UserA"},
            ["Authorization", "Cookie"]
        ),
        (
            set(),
            {"id": "1", "name": "UserA", "password": "hash"},
            {"id": "1", "name": "UserA", "password": "hash"},
            []
        )
    ]
)
async def test_router_schema_projection_pruning(
    monkeypatch: pytest.MonkeyPatch,
    restricted_fields: set[str],
    payload_in: dict[str, Any],
    expected_payload_out: dict[str, Any],
    expected_vary: list[str]
) -> None:
    monkeypatch.setattr("zcore.web.api_router.get_restricted_fields", lambda: restricted_fields)
    
    app = FastAPI()
    mock_service = TargetService(payload_in)
    container.register_singleton(TargetService, mock_service)
    
    class TargetRouter(BaseRouter[DummyCreate, DummyUpdate]):
        model = DummyModel
        create_schema = DummyCreate
        update_schema = DummyUpdate
        schema_out = DummyOut
        service = TargetService
        DEFAULT_PERMISSIONS = []
        prefix = "/items"
        expose_schemas = True

    router_inst = TargetRouter()
    app.include_router(router_inst.router)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/items/12345678-1234-5678-1234-567812345678")
        assert response.status_code == 200
        
        json_data = response.json()
        assert json_data["data"] == expected_payload_out

        vary_header = response.headers.get("vary", "")
        for header in expected_vary:
            assert header.lower() in vary_header.lower()

        if expected_vary:
            schema_resp = await client.get("/items/?schema=true")
            assert schema_resp.status_code == 200
            schema_data = schema_resp.json()
            assert "password" not in schema_data["data"]["properties"]

@pytest.mark.anyio
@pytest.mark.parametrize(
    "custom_request_id, expect_valid_uuid",
    [
        ("my-custom-request-id-123", False),
        (None, True),
    ]
)
async def test_request_id_middleware(custom_request_id: str | None, expect_valid_uuid: bool) -> None:
    app = FastAPI()
    app.add_middleware(RequestLogMiddleware)

    @app.get("/health")
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {}
        if custom_request_id:
            headers["x-request-id"] = custom_request_id

        response = await client.get("/health", headers=headers)
        assert response.status_code == 200
        
        response_id = response.headers.get("x-request-id")
        assert response_id is not None
        
        if expect_valid_uuid:
            assert uuid.UUID(response_id)
        else:
            assert response_id == custom_request_id