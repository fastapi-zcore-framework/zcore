import inspect
from typing import Callable, Coroutine, Any, get_origin, get_args
from contextlib import AsyncExitStack

from fastapi import Request, Response
from fastapi.routing import APIRoute
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.dependencies.utils import solve_dependencies

from pydantic import BaseModel

from zcore.utils.helpers import json_dumps, json_loads
from zcore.web.response import ResponseWrapper

class ZCoreRequest(Request):
    async def body(self) -> bytes:
        if not hasattr(self, "_cached_body"):
            self._cached_body = await super().body()
        return self._cached_body

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

def prune_nested_field(data: Any, path_parts: list[str]) -> None:
    if not path_parts or data is None:
        return
    
    field = path_parts[0]
    
    if len(path_parts) == 1:
        if isinstance(data, dict):
            data.pop(field, None)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    item.pop(field, None)
        return

    if isinstance(data, dict):
        next_node = data.get(field)
        if next_node is not None:
            prune_nested_field(next_node, path_parts[1:])
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                next_node = item.get(field)
                if next_node is not None:
                    prune_nested_field(next_node, path_parts[1:])

def prune_response_body(body_bytes: bytes, hidden_fields: set[str]) -> bytes:
    try:
        data = json_loads(body_bytes.decode("utf-8"))
    except Exception:
        return body_bytes
        
    payload_data = data.get("data")
    if payload_data is not None:
        for path in hidden_fields:
            path_parts = path.split(".")
            if path_parts[0] == "resource" and len(path_parts) > 1:
                prune_nested_field(payload_data, path_parts[1:])
            else:
                prune_nested_field(payload_data, path_parts)
                            
    meta = data.get("meta") or {}
    meta["restricted_fields"] = list(hidden_fields)
    data["meta"] = meta
    
    return json_dumps(data).encode("utf-8")

class ZCoreAPIRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Coroutine[None, None, Response]]:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            zcore_request = ZCoreRequest(request.scope, request._receive)
            
            if zcore_request.query_params.get("schema") == "true":
                async with AsyncExitStack() as async_exit_stack:
                    solve_kwargs = {
                        "request": zcore_request,
                        "dependant": self.dependant,
                        "async_exit_stack": async_exit_stack,
                        "dependency_overrides_provider": getattr(self, "dependency_overrides_provider", None),
                    }
                    
                    sig = inspect.signature(solve_dependencies)
                    if "embed_body_fields" in sig.parameters:
                        body_field = getattr(self, "body_field", None)
                        embed = getattr(body_field.field_info, "embed", False) if body_field and hasattr(body_field, "field_info") else False
                        solve_kwargs["embed_body_fields"] = embed

                    solved_result = await solve_dependencies(**solve_kwargs)
                    
                    errors = getattr(solved_result, "errors", [])
                    if isinstance(solved_result, tuple) and len(solved_result) >= 2:
                        errors = solved_result[1]
                        
                    if errors:
                        filtered_errors = []
                        for error in errors:
                            loc = error.get("loc", []) if isinstance(error, dict) else getattr(error, "loc", [])
                            if not loc or loc[0] != "body":
                                filtered_errors.append(error)
                        
                        if filtered_errors:
                            raise RequestValidationError(filtered_errors)
                
                target_model = None
                if zcore_request.method in ["POST", "PUT", "PATCH"]:
                    target_model = find_input_schema(self.dependant)
                else:
                    target_model = find_output_schema(self.response_model)

                if not target_model:
                    return JSONResponse(
                        status_code=400,
                        content={"success": False, "message": "No schema defined for this endpoint."}
                    )
                
                schema_dict = target_model.model_json_schema()
                hidden_fields = getattr(zcore_request.state, "hidden_fields", set())
                
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
            hidden_fields = getattr(zcore_request.state, "hidden_fields", None)
            
            if hidden_fields and "application/json" in response.headers.get("content-type", "").lower():
                if hasattr(response, "body"):
                    new_body = prune_response_body(response.body, hidden_fields)
                    response.body = new_body
                    response.headers["content-length"] = str(len(new_body))
                    
                    vary = response.headers.get("vary", "")
                    if vary:
                        if "authorization" not in vary.lower():
                            response.headers["vary"] = f"{vary}, Authorization"
                    else:
                        response.headers["vary"] = "Authorization"
            return response

        return custom_route_handler