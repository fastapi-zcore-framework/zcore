import uuid
from enum import StrEnum
from typing import TypeVar, Generic, Type, Any, Optional, Union, TYPE_CHECKING
from pydantic import BaseModel
from fastapi import APIRouter, status, Depends
from fastapi.routing import APIRoute

from zcore.security.permissions import HasScopes
from zcore.web.response import ResponseWrapper
from zcore.web.api_router import ZCoreAPIRoute
from zcore.db.search import SearchRequest
from zcore.service.base import BaseService
from zcore.kernel.di import Inject

if TYPE_CHECKING:
   from zcore.db.pagination import BasePagination

CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class RouteKey(StrEnum):
    POST = "POST"
    GET = "GET"
    GET_ALL = "GET_ALL"
    SEARCH = "SEARCH"
    UPDATE = "UPDATE"
    PATCH = "PATCH"
    DELETE = "DELETE"

class BaseRouter(Generic[CreateSchemaType, UpdateSchemaType]):
    model: Type[Any]
    create_schema: Optional[Type[CreateSchemaType]] = None
    update_schema: Optional[Type[UpdateSchemaType]] = None
    schema_out: Optional[Type[BaseModel]] = None
    service: Any = None

    prefix: str = ""
    tags: Optional[list[str]] = None
    exclude: Optional[set[RouteKey]] = None
    pagination_class: Optional[Type["BasePagination"]] = None
    route_class: Type[APIRoute] = ZCoreAPIRoute

    expose_schemas: Union[set[RouteKey], bool] = False

    DEFAULT_PERMISSIONS: Optional[Union[list[Any], str]] = "AUTO"
    POST_PERMISSIONS: Optional[list[Any]] = None
    GET_PERMISSIONS: Optional[list[Any]] = None
    GET_ALL_PERMISSIONS: Optional[list[Any]] = None
    SEARCH_PERMISSIONS: Optional[list[Any]] = None
    UPDATE_PERMISSIONS: Optional[list[Any]] = None
    PATCH_PERMISSIONS: Optional[list[Any]] = None
    DELETE_PERMISSIONS: Optional[list[Any]] = None

    def __init__(self) -> None:
        # Fail-Fast Startup Verification
        if not self.service:
            raise ValueError(f"Service class must be defined in '{self.__class__.__name__}'.")
            
        self.router = APIRouter(
            prefix=self.prefix,
            tags=self.tags or [],
            route_class=self.route_class
        )
        self.exclude = self.exclude or set()
        self._validate_schema_configurations()
        self._register_routes()

    def _validate_schema_configurations(self) -> None:
        """Startup check to ensure that routes requiring input schemas are not configured as None."""
        if RouteKey.POST not in self.exclude and self.create_schema is None:
            raise ValueError(f"POST route is enabled in '{self.__class__.__name__}', but 'create_schema' is None.")
        if (RouteKey.UPDATE not in self.exclude or RouteKey.PATCH not in self.exclude) and self.update_schema is None:
            raise ValueError(f"UPDATE/PATCH route is enabled in '{self.__class__.__name__}', but 'update_schema' is None.")

    def _get_openapi_extra(self, route_key: RouteKey) -> Optional[dict[str, Any]]:
        if isinstance(self.expose_schemas, bool):
            expose = self.expose_schemas
        else:
            expose = route_key in (self.expose_schemas or set())
        
        if expose:
            return {"expose_schema": True}
        return None

    def _normalize_dependencies(self, raw_deps: Union[list[Any], Any]) -> list[Depends]:
        if raw_deps is None:
            return []
        
        deps_list = raw_deps if isinstance(raw_deps, list) else [raw_deps]
        normalized: list[Depends] = []
        
        for dep in deps_list:
            if isinstance(dep, Depends):
                normalized.append(dep)
            else:
                normalized.append(Depends(dep))
                
        return normalized

    def _get_route_dependencies(self, route_key: RouteKey) -> list[Depends]:
        route_perms = getattr(self, f"{route_key.value}_PERMISSIONS", None)
        
        if route_perms == []:
            return []
        
        if route_perms is not None:
            return self._normalize_dependencies(route_perms)
        
        if self.DEFAULT_PERMISSIONS != "AUTO":
            if not self.DEFAULT_PERMISSIONS:
                return []
            return self._normalize_dependencies(self.DEFAULT_PERMISSIONS)

        if self.DEFAULT_PERMISSIONS == "AUTO" and not self.model:
            raise ValueError(f"Model class must be defined in {self.__class__.__name__} to use AUTO permissions.")
        
        action_map = {
            RouteKey.POST: self.model.actions().CREATE,
            RouteKey.GET: self.model.actions().VIEW,
            RouteKey.GET_ALL: self.model.actions().LISTVIEW,
            RouteKey.SEARCH: self.model.actions().LISTVIEW,
            RouteKey.UPDATE: self.model.actions().UPDATE,
            RouteKey.PATCH: self.model.actions().UPDATE,
            RouteKey.DELETE: self.model.actions().DELETE,
        }
        scope = action_map.get(route_key)
        
        return self._normalize_dependencies(HasScopes(scope))

    def _register_routes(self) -> None:
        service_callable = self.service
        service_dependency = Inject(service_callable)

        if RouteKey.POST not in self.exclude:
            c_schema = self.create_schema
            async def _create_endpoint(data_in: c_schema, service_inst: BaseService = service_dependency) -> ResponseWrapper:
                return await self.create_endpoint(data_in, service_inst)
            
            self.router.add_api_route(
                path="/",
                endpoint=_create_endpoint,
                methods=["POST"],
                dependencies=self._get_route_dependencies(RouteKey.POST),
                status_code=status.HTTP_201_CREATED,
                response_model=ResponseWrapper[self.schema_out] if self.schema_out else ResponseWrapper,
                openapi_extra=self._get_openapi_extra(RouteKey.POST)
            )

        if RouteKey.GET not in self.exclude:
            async def _get_endpoint(id: uuid.UUID, service_inst: BaseService = service_dependency) -> ResponseWrapper:
                return await self.get_endpoint(id, service_inst)

            self.router.add_api_route(
                path="/{id}",
                endpoint=_get_endpoint,
                methods=["GET"],
                dependencies=self._get_route_dependencies(RouteKey.GET),
                status_code=status.HTTP_200_OK,
                response_model=ResponseWrapper[self.schema_out] if self.schema_out else ResponseWrapper,
                openapi_extra=self._get_openapi_extra(RouteKey.GET)
            )

        if RouteKey.GET_ALL not in self.exclude:
            if self.pagination_class:
                params_class = self.pagination_class.params_class
                
                async def _get_all_endpoint(params: params_class = Depends(), service_inst: BaseService = service_dependency) -> ResponseWrapper:
                    return await self.get_all_endpoint(service_inst, params)
            else:
                async def _get_all_endpoint(service_inst: BaseService = service_dependency) -> ResponseWrapper:
                    return await self.get_all_endpoint(service_inst)

            self.router.add_api_route(
                path="/",
                endpoint=_get_all_endpoint,
                methods=["GET"],
                dependencies=self._get_route_dependencies(RouteKey.GET_ALL),
                status_code=status.HTTP_200_OK,
                response_model=ResponseWrapper[list[self.schema_out]] if self.schema_out else ResponseWrapper,
                openapi_extra=self._get_openapi_extra(RouteKey.GET_ALL)
            )

        if RouteKey.SEARCH not in self.exclude:
            async def _search_endpoint(search_in: SearchRequest, service_inst: BaseService = service_dependency) -> ResponseWrapper:
                return await self.search_endpoint(search_in, service_inst)

            self.router.add_api_route(
                path="/search",
                endpoint=_search_endpoint,
                methods=["POST"],
                dependencies=self._get_route_dependencies(RouteKey.SEARCH),
                status_code=status.HTTP_200_OK,
                response_model=ResponseWrapper[list[self.schema_out]] if self.schema_out else ResponseWrapper,
                openapi_extra=self._get_openapi_extra(RouteKey.SEARCH)
            )

        if RouteKey.UPDATE not in self.exclude:
            u_schema = self.update_schema
            
            async def _update_endpoint(id: uuid.UUID, data_in: u_schema, service_inst: BaseService = service_dependency) -> ResponseWrapper:
                return await self.update_endpoint(id, data_in, service_inst)

            self.router.add_api_route(
                path="/{id}",
                endpoint=_update_endpoint,
                methods=["PUT"],
                dependencies=self._get_route_dependencies(RouteKey.UPDATE),
                status_code=status.HTTP_200_OK,
                response_model=ResponseWrapper[self.schema_out] if self.schema_out else ResponseWrapper,
                openapi_extra=self._get_openapi_extra(RouteKey.UPDATE)
            )

        if RouteKey.PATCH not in self.exclude:
            u_schema = self.update_schema
            
            async def _patch_endpoint(id: uuid.UUID, data_in: u_schema, service_inst: BaseService = service_dependency) -> ResponseWrapper:
                return await self.patch_endpoint(id, data_in, service_inst)
                
            self.router.add_api_route(
                path="/{id}",
                endpoint=_patch_endpoint,
                methods=["PATCH"],
                dependencies=self._get_route_dependencies(RouteKey.PATCH),
                status_code=status.HTTP_200_OK,
                response_model=ResponseWrapper[self.schema_out] if self.schema_out else ResponseWrapper,
                openapi_extra=self._get_openapi_extra(RouteKey.PATCH)
            )

        if RouteKey.DELETE not in self.exclude:
            async def _delete_endpoint(id: uuid.UUID, service_inst: BaseService = service_dependency) -> ResponseWrapper:
                return await self.delete_endpoint(id, service_inst)

            self.router.add_api_route(
                path="/{id}",
                endpoint=_delete_endpoint,
                methods=["DELETE"],
                dependencies=self._get_route_dependencies(RouteKey.DELETE),
                status_code=status.HTTP_200_OK,
                response_model=ResponseWrapper,
                openapi_extra=self._get_openapi_extra(RouteKey.DELETE)
            )
            
    async def create_endpoint(self, data_in: CreateSchemaType, service: BaseService) -> ResponseWrapper:
        data = await service.create(data_in)
        return ResponseWrapper(data=data)
    
    async def get_endpoint(self, id: uuid.UUID, service: BaseService) -> ResponseWrapper:
        data = await service.get(id)
        return ResponseWrapper(data=data)
    
    async def get_all_endpoint(self, service: BaseService, pagination: Any = None) -> ResponseWrapper:
        result = await service.get_list(pagination)
        from zcore.db.pagination import PaginatedResult
        if isinstance(result, PaginatedResult):
            return ResponseWrapper(data=result.data, meta=result.meta)
        return ResponseWrapper(data=result)
    
    async def search_endpoint(self, search_in: SearchRequest, service: BaseService) -> ResponseWrapper:
        pagination = None
        from zcore.db.pagination import PageNumberParams, CursorParams
        if self.pagination_class:
            if self.pagination_class.params_class == CursorParams:
                pagination = CursorParams(cursor=search_in.cursor, size=search_in.size)
            else:
                pagination = PageNumberParams(page=search_in.page, size=search_in.size)

        result = await service.search(search_in, pagination)
        from zcore.db.pagination import PaginatedResult
        if isinstance(result, PaginatedResult):
            return ResponseWrapper(data=result.data, meta=result.meta)
        return ResponseWrapper(data=result)
    
    async def update_endpoint(self, id: uuid.UUID, data_in: UpdateSchemaType, service: BaseService) -> ResponseWrapper:
        data = await service.update(id, data_in)
        return ResponseWrapper(data=data)
    
    async def patch_endpoint(self, id: uuid.UUID, data_in: UpdateSchemaType, service: BaseService) -> ResponseWrapper:
        data = await service.update(id, data_in, partial=True)
        return ResponseWrapper(data=data)
    
    async def delete_endpoint(self, id: uuid.UUID, service: BaseService) -> ResponseWrapper:
        await service.delete(id)
        return ResponseWrapper(message="Deleted successfully")