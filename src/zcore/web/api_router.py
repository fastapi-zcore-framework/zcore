import copy
from typing import Callable, Coroutine, Any, get_origin, get_args, Union
from fastapi import Request, Response
from fastapi.routing import APIRoute
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from zcore.utils.helpers import json_dumps
from zcore.web.response import ResponseWrapper
from zcore.web.projection import ResponseProjector
from zcore.context.context import get_restricted_fields

class ZCoreRequest(Request):
    _cached_body: bytes

    async def body(self) -> bytes:
        if not hasattr(self, "_cached_body"):
            self._cached_body = await super().body()
        return self._cached_body

class ZCoreJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        restricted_fields = get_restricted_fields()
        if restricted_fields and content is not None:
            content = ResponseProjector.project(content, restricted_fields)
        return json_dumps(content).encode("utf-8")

def find_input_schema(dependant: Any) -> type[BaseModel] | None:
    for param in getattr(dependant, "body_params", []):
        annotation = getattr(param.field_info, "annotation", None) or getattr(param, "type_", None)
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return annotation
    return None

def find_output_schema(response_model: Any) -> type[BaseModel] | None:
    if response_model is None:
        return None
    origin = get_origin(response_model)
    args = get_args(response_model)
    if origin is None:
        if isinstance(response_model, type) and issubclass(response_model, BaseModel):
            return response_model
        return None
    for arg in args:
        schema = find_output_schema(arg)
        if schema:
            return schema
    return None

def prune_json_schema(schema: dict[str, Any], path: str) -> None:
    parts = path.split(".")
    if parts[0] == "resource" and len(parts) > 1:
        parts = parts[1:]
    
    def prune_node(node: Any, path_parts: list[str]) -> None:
        if not isinstance(node, dict):
            return
        if "$ref" in node:
            ref_path = node["$ref"].split("/")
            target = schema
            for key in ref_path[1:]:
                if isinstance(target, dict):
                    target = target.get(key)
            prune_node(target, path_parts)
            return
        properties = node.get("properties")
        if isinstance(properties, dict):
            first_part = path_parts[0]
            if first_part in properties:
                if len(path_parts) == 1:
                    properties.pop(first_part)
                    required = node.get("required")
                    if isinstance(required, list) and first_part in required:
                        required.remove(first_part)
                else:
                    prune_node(properties[first_part], path_parts[1:])
        for k, v in node.items():
            if k != "properties":
                if isinstance(v, dict):
                    prune_node(v, path_parts)
                elif isinstance(v, list):
                    for item in v:
                        prune_node(item, path_parts)

    prune_node(schema, parts)

class ZCoreAPIRoute(APIRoute):
    expose_schema: bool
    target_model: type[BaseModel] | None
    _cached_raw_schema: dict[str, Any] | None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        
        self.expose_schema = False
        if self.openapi_extra and isinstance(self.openapi_extra, dict):
            if self.openapi_extra.get("expose_schema"):
                self.expose_schema = True

        self.target_model = None
        self._cached_raw_schema = None

        if self.expose_schema:
            if self.methods and any(m in ["POST", "PUT", "PATCH"] for m in self.methods):
                self.target_model = find_input_schema(self.dependant)
            else:
                self.target_model = find_output_schema(self.response_model)

            if self.target_model:
                self._cached_raw_schema = self.target_model.model_json_schema()

        current_class = self.response_class
        if hasattr(current_class, "value"):
            current_class = getattr(current_class, "value")
        if current_class == JSONResponse:
            self.response_class = ZCoreJSONResponse

    def get_route_handler(self) -> Callable[[Request], Coroutine[None, None, Response]]:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            zcore_request = ZCoreRequest(request.scope, request._receive)
            
            if self.expose_schema and zcore_request.query_params.get("schema") == "true":
                if not self._cached_raw_schema:
                    return JSONResponse(
                        status_code=400,
                        content={"success": False, "message": "No schema defined for this endpoint."}
                    )
                
                schema_dict = copy.deepcopy(self._cached_raw_schema)
                hidden_fields = get_restricted_fields()
                for field_path in hidden_fields:
                    prune_json_schema(schema_dict, field_path)
                
                response_payload = ResponseWrapper(
                    success=True,
                    message="Schema generated successfully",
                    data=schema_dict,
                    meta={"restricted_fields": list(hidden_fields)}
                )
                return JSONResponse(content=response_payload.model_dump())

            response: Response = await original_route_handler(zcore_request)
            
            hidden_fields = get_restricted_fields()
            if hidden_fields and "application/json" in response.headers.get("content-type", "").lower():
                vary = response.headers.get("vary", "")
                target_vary_headers = ["Authorization", "Cookie"]
                existing_vary = [v.strip().lower() for v in vary.split(",")] if vary else []
                
                new_vary_elements = [v for v in target_vary_headers if v.lower() not in existing_vary]
                if new_vary_elements:
                    if vary:
                        response.headers["vary"] = f"{vary}, {', '.join(new_vary_elements)}"
                    else:
                        response.headers["vary"] = ", ".join(new_vary_elements)
            return response

        return custom_route_handler