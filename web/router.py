import uuid

from dataclasses import dataclass
from enum import StrEnum
from typing import TypeVar, Generic, Type
from pydantic import BaseModel
from fastapi import APIRouter, status, Depends

from app.core.security.permissions import PermissionChecker
from app.core.web.response import ResponseWrapper
from app.core.db.search import SearchRequest
from app.core.db.service import BaseService
from app.core.db.setup import Actions

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
    depends: tuple[str, ...] = ()
    response_model: type[BaseModel] | None = None
    status_code: int = status.HTTP_200_OK
    
def crud_specs(response_model: type[BaseModel] | None) -> dict[RouteKey, RouteSpec]:
    spec = RouteSpec(response_model=response_model)
    return {
        RouteKey.POST: spec,
        RouteKey.GET: spec,
        RouteKey.GET_ALL: spec,
        RouteKey.SEARCH: spec,
        RouteKey.UPDATE: spec,
        RouteKey.PATCH: spec,
        RouteKey.DELETE: spec,
    }


class BaseRouter(Generic[CreateSchemaType, UpdateSchemaType]):
    """
    ```
    from app.core.test import BaseRouter, crud_specs
    from app.modules.auth.service import RoleService

    roles_router = BaseRouter(
        specs=crud_specs(RolePublic),
        create_schema= RoleCreate,
        update_schema= RoleUpdate,
        prefix="/roles",
        tags=['Roles'],
        service_dep= RoleService,
    )

    router.include_router(
        roles_router.router,
        prefix='/hr',
        tags=['Roles']
    )
    ```
    """
    def __init__(
        self,
        specs: dict[RouteKey, RouteSpec],
        create_schema: Type[CreateSchemaType],
        update_schema: Type[UpdateSchemaType],
        service_dep: BaseService,
        prefix: str = "",
        tags: list[str] = None,
        exclude: set[RouteKey] | None = None,
    ):       
        self.router = APIRouter(prefix=prefix, tags=tags or [])
        self.specs = specs
        self.exclude = exclude or set()
        self.service_dep = service_dep
        self.create_schema = create_schema
        self.update_schema = update_schema
        self._register_routes()

    def _get_deps(self, key: RouteKey) -> list[Depends]:
        perms = self.specs[key].depends
        if not perms:
            return []
        checker = PermissionChecker.required(perms)
        return [Depends(checker)] if checker else []

    def _register_routes(self):
        s_dep = self.service_dep
        c_schema = self.create_schema
        u_schema = self.update_schema

        if RouteKey.POST not in self.exclude:
            async def create_endpoint(data_in: c_schema, service: BaseService = Depends(s_dep)):
                data = await service.create(data_in)
                return ResponseWrapper(data=data)
            
            self.router.add_api_route(
                path="/",
                endpoint=create_endpoint,
                methods=["POST"],
                dependencies=self._get_deps(RouteKey.POST),
                response_model=ResponseWrapper[self.specs[RouteKey.POST].response_model]
            )

        if RouteKey.GET not in self.exclude:
            async def get_endpoint(id: uuid.UUID, service: BaseService = Depends(s_dep)):
                data = await service.get(id)
                return ResponseWrapper(data=data)

            self.router.add_api_route(
                path="/{id}",
                endpoint=get_endpoint,
                methods=["GET"],
                dependencies=self._get_deps(RouteKey.GET),
                response_model=ResponseWrapper[self.specs[RouteKey.GET].response_model]
            )

        if RouteKey.GET_ALL not in self.exclude:
            async def get_all_endpoint(limit: int = 100, skip: int = 0, service: BaseService = Depends(s_dep)):
                data = await service.get_all(limit=limit, skip=skip)
                return ResponseWrapper(data=data, meta={"limit": limit, "skip": skip})

            self.router.add_api_route(
                path="/",
                endpoint=get_all_endpoint,
                methods=["GET"],
                dependencies=self._get_deps(RouteKey.GET_ALL),
                response_model=ResponseWrapper[list[self.specs[RouteKey.GET_ALL].response_model]]
            )

        if RouteKey.SEARCH not in self.exclude:
            async def search_endpoint(search_in: SearchRequest, service: BaseService = Depends(s_dep)):
                result = await service.search(search_in)
                return ResponseWrapper(data=result)

            self.router.add_api_route(
                path="/search",
                endpoint=search_endpoint,
                methods=["POST"], # جستجو با Body معمولاً POST است
                dependencies=self._get_deps(RouteKey.SEARCH),
                response_model=ResponseWrapper[list[self.specs[RouteKey.SEARCH].response_model]]
            )

        if RouteKey.UPDATE not in self.exclude:
            async def update_endpoint(id: uuid.UUID, data_in: u_schema, service: BaseService = Depends(s_dep)):
                data = await service.update(id, data_in)
                return ResponseWrapper(data=data)

            self.router.add_api_route(
                path="/{id}",
                endpoint=update_endpoint,
                methods=["PUT"],
                dependencies=self._get_deps(RouteKey.UPDATE),
                response_model=ResponseWrapper[self.specs[RouteKey.UPDATE].response_model]
            )

        if RouteKey.PATCH not in self.exclude:
            async def patch_endpoint(id: uuid.UUID, data_in: u_schema, service: BaseService = Depends(s_dep)):
                data = await service.update(id, data_in, auto_commit=False)
                return ResponseWrapper(data=data)

            self.router.add_api_route(
                path="/{id}",
                endpoint=patch_endpoint,
                methods=["PATCH"],
                dependencies=self._get_deps(RouteKey.PATCH),
                response_model=ResponseWrapper[self.specs[RouteKey.PATCH].response_model]
            )

        if RouteKey.DELETE not in self.exclude:
            async def delete_endpoint(id: uuid.UUID, service: BaseService = Depends(s_dep)):
                await service.delete(id)
                return ResponseWrapper(message="Deleted successfully")

            self.router.add_api_route(
                path="/{id}",
                endpoint=delete_endpoint,
                methods=["DELETE"],
                dependencies=self._get_deps(RouteKey.DELETE),
                status_code=status.HTTP_200_OK
            )