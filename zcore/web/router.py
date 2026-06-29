import uuid

from dataclasses import dataclass
from enum import StrEnum
from typing import TypeVar, Generic, Type, Any
from pydantic import BaseModel
from fastapi import APIRouter, status, Depends
from fastapi.routing import APIRoute

from zcore.web.response import ResponseWrapper
from zcore.db.search import SearchRequest
from zcore.service.base import BaseService
from zcore.db.pagination import PaginatedResult, BasePagination, PageNumberParams, CursorParams

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
    
@dataclass(frozen=True, slots=True)
class RouteSpec:
    depends: tuple[Depends, ...] = ()
    response_model: type[BaseModel] | None = None
    status_code: int = status.HTTP_200_OK
    
def crud_specs(response_model: type[BaseModel] | None) -> dict[RouteKey, RouteSpec]:
    return {
        RouteKey.POST: RouteSpec(response_model=response_model, status_code=status.HTTP_201_CREATED),
        RouteKey.GET: RouteSpec(response_model=response_model),
        RouteKey.GET_ALL: RouteSpec(response_model=response_model),
        RouteKey.SEARCH: RouteSpec(response_model=response_model),
        RouteKey.UPDATE: RouteSpec(response_model=response_model),
        RouteKey.PATCH: RouteSpec(response_model=response_model),
        RouteKey.DELETE: RouteSpec(),
    }

class BaseRouter(Generic[CreateSchemaType, UpdateSchemaType]):
    def __init__(
        self,
        specs: dict[RouteKey, RouteSpec],
        create_schema: Type[CreateSchemaType],
        update_schema: Type[UpdateSchemaType],
        service_dep: BaseService,
        prefix: str = "",
        tags: list[str] = None,
        exclude: set[RouteKey] | None = None,
        pagination_class: Type[BasePagination] | None = None,
        route_class: Type[APIRoute] = APIRoute,
    ):       
        self.router = APIRouter(prefix=prefix, tags=tags or [], route_class=route_class)
        self.specs = specs
        self.exclude = exclude or set()
        self.service_dep = service_dep
        self.create_schema = create_schema
        self.update_schema = update_schema
        self.pagination_class = pagination_class
        self._register_routes()
    
    def _get_spec(self, key: RouteKey) -> RouteSpec:
        return self.specs[key]

    def _register_routes(self):
        s_dep = self.service_dep
        c_schema = self.create_schema
        u_schema = self.update_schema

        if RouteKey.POST not in self.exclude:
            spec = self._get_spec(RouteKey.POST)
            async def _create_endpoint(data_in: c_schema, service: BaseService = Depends(s_dep)):
                return await self.create_endpoint(data_in, service)
            
            self.router.add_api_route(
                path="/",
                endpoint=_create_endpoint,
                methods=["POST"],
                dependencies=list(spec.depends),
                status_code=spec.status_code,
                response_model=ResponseWrapper[spec.response_model]
            )

        if RouteKey.GET not in self.exclude:
            spec = self._get_spec(RouteKey.GET)
            async def _get_endpoint(id: uuid.UUID, service: BaseService = Depends(s_dep)):
                return await self.get_endpoint(id, service)

            self.router.add_api_route(
                path="/{id}",
                endpoint=_get_endpoint,
                methods=["GET"],
                dependencies=list(spec.depends),
                status_code=spec.status_code,
                response_model=ResponseWrapper[spec.response_model]
            )

        if RouteKey.GET_ALL not in self.exclude:
            spec = self._get_spec(RouteKey.GET_ALL)
            
            if self.pagination_class:
                params_class = self.pagination_class.params_class
                async def _get_all_endpoint(params: params_class = Depends(), service: BaseService = Depends(s_dep)):
                    return await self.get_all_endpoint(service, params)
            else:
                async def _get_all_endpoint(service: BaseService = Depends(s_dep)):
                    return await self.get_all_endpoint(service)

            self.router.add_api_route(
                path="/",
                endpoint=_get_all_endpoint,
                methods=["GET"],
                dependencies=list(spec.depends),
                status_code=spec.status_code,
                response_model=ResponseWrapper[list[spec.response_model]]
            )

        if RouteKey.SEARCH not in self.exclude:
            spec = self._get_spec(RouteKey.SEARCH)
            async def _search_endpoint(search_in: SearchRequest, service: BaseService = Depends(s_dep)):
                return await self.search_endpoint(search_in, service)

            self.router.add_api_route(
                path="/search",
                endpoint=_search_endpoint,
                methods=["POST"],
                dependencies=list(spec.depends),
                status_code=spec.status_code,
                response_model=ResponseWrapper[list[spec.response_model]]
            )

        if RouteKey.UPDATE not in self.exclude:
            spec = self._get_spec(RouteKey.UPDATE)
            async def _update_endpoint(id: uuid.UUID, data_in: u_schema, service: BaseService = Depends(s_dep)):
                return await self.update_endpoint(id, data_in, service)

            self.router.add_api_route(
                path="/{id}",
                endpoint=_update_endpoint,
                methods=["PUT"],
                dependencies=list(spec.depends),
                status_code=spec.status_code,
                response_model=ResponseWrapper[spec.response_model]
            )

        if RouteKey.PATCH not in self.exclude:
            spec = self._get_spec(RouteKey.PATCH)
            async def _patch_endpoint(id: uuid.UUID, data_in: u_schema, service: BaseService = Depends(s_dep)):
                return await self.patch_endpoint(id, data_in, service)
                
            self.router.add_api_route(
                path="/{id}",
                endpoint=_patch_endpoint,
                methods=["PATCH"],
                dependencies=list(spec.depends),
                status_code=spec.status_code,
                response_model=ResponseWrapper[spec.response_model]
            )

        if RouteKey.DELETE not in self.exclude:
            spec = self._get_spec(RouteKey.DELETE)
            async def _delete_endpoint(id: uuid.UUID, service: BaseService = Depends(s_dep)):
                return await self.delete_endpoint(id, service)

            self.router.add_api_route(
                path="/{id}",
                endpoint=_delete_endpoint,
                methods=["DELETE"],
                dependencies=list(spec.depends),
                status_code=spec.status_code,
                response_model=ResponseWrapper
            )
            
    async def create_endpoint(self, data_in: CreateSchemaType, service: BaseService) -> ResponseWrapper:
        data = await service.create(data_in)
        return ResponseWrapper(data=data)
    
    async def get_endpoint(self, id: uuid.UUID, service: BaseService) -> ResponseWrapper:
        data = await service.get(id)
        return ResponseWrapper(data=data)
    
    async def get_all_endpoint(self, service: BaseService, pagination: Any = None) -> ResponseWrapper:
        result = await service.get_list(pagination)
        if isinstance(result, PaginatedResult):
            return ResponseWrapper(data=result.data, meta=result.meta)
        return ResponseWrapper(data=result)
    
    async def search_endpoint(self, search_in: SearchRequest, service: BaseService) -> ResponseWrapper:
        pagination = None
        if self.pagination_class:
            if self.pagination_class.params_class == CursorParams:
                pagination = CursorParams(cursor=search_in.cursor, size=search_in.size)
            else:
                pagination = PageNumberParams(page=search_in.page, size=search_in.size)

        result = await service.search(search_in, pagination)
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