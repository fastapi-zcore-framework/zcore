from pydantic import BaseModel
from typing import Generic, TypeVar, Type, Any, Sequence

from sqlalchemy.orm.interfaces import ExecutableOption

from zcore.exceptions.base import EntityNotFound

from zcore.db.setup import Base
from zcore.db.repository import BaseRepository
from zcore.db.search import SearchRequest

ModelType = TypeVar("ModelType", bound=Base)        
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class ReadServiceMixin(Generic[ModelType]):
    repository: BaseRepository
    model: Type[ModelType]

    async def post_get(self, model: ModelType) -> ModelType:
        return model

    async def post_get_multi(self, models: Sequence[ModelType]) -> Sequence[ModelType]:
        return models

    async def exist(self, id: Any) -> bool:
        return await self.repository.exist(id)

    async def get(self, id: Any, fields: list[Any] = None, options: list[ExecutableOption] = None) -> ModelType:
        result = await self.repository.get(id, fields, options)
        if not result:
            raise EntityNotFound(message=f"{self.model.__name__} not found.")
        return await self.post_get(result)

    async def get_by_ids(self, ids: list[Any], fields: list[Any] = None, options: list[ExecutableOption] = None) -> Sequence[ModelType]:
        result = await self.repository.get_by_ids(ids, fields, options)
        return await self.post_get_multi(result)

    async def get_list(self, pagination: Any = None, fields: list[Any] = None, options: list[ExecutableOption] = None) -> Any:
        result = await self.repository.get_list(pagination, fields, options)
        if pagination is None:
            return await self.post_get_multi(result)
        result.data = await self.post_get_multi(result.data)
        return result

class WriteServiceMixin(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    repository: BaseRepository
    model: Type[ModelType]

    async def pre_create(self, schema: CreateSchemaType) -> None: pass
    async def post_create(self, model: ModelType) -> None: pass
    
    async def pre_create_multi(self, schemas: list[CreateSchemaType]) -> None: pass
    async def post_create_multi(self, models: Sequence[ModelType]) -> None: pass

    async def pre_update(self, id: Any, schema: UpdateSchemaType, partial: bool) -> None: pass
    async def post_update(self, model: ModelType) -> None: pass
    
    async def pre_update_multi(self, data: dict[Any, UpdateSchemaType], partial: bool) -> None: pass
    async def post_update_multi(self, models: Sequence[ModelType]) -> None: pass

    async def pre_delete(self, id: Any) -> None: pass
    async def post_delete(self, model: ModelType) -> None: pass
    
    async def pre_delete_multi(self, ids: list[Any]) -> None: pass
    async def post_delete_multi(self, models: Sequence[ModelType]) -> None: pass

    async def create(self, schema: CreateSchemaType) -> ModelType:
        await self.pre_create(schema)
        result = await self.repository.create(schema)
        await self.post_create(result)
        return result

    async def create_multi(self, schemas: list[CreateSchemaType]) -> Sequence[ModelType]:
        await self.pre_create_multi(schemas)
        result = await self.repository.create_multi(schemas)
        await self.post_create_multi(result)
        return result

    async def update(self, id: Any, schema: UpdateSchemaType, partial: bool = False) -> ModelType:
        await self.pre_update(id, schema, partial)
        result = await self.repository.update(id, schema, partial)
        if not result:
            raise EntityNotFound(message=f"{self.model.__name__} not found.")
        await self.post_update(result)
        return result

    async def update_multi(self, data: dict[Any, UpdateSchemaType], partial: bool = False) -> Sequence[ModelType]:
        await self.pre_update_multi(data, partial)
        result = await self.repository.update_multi(data, partial)
        await self.post_update_multi(result)
        return result

    async def delete(self, id: Any) -> ModelType:
        await self.pre_delete(id)
        result = await self.repository.delete(id)
        if not result:
            raise EntityNotFound(message=f"{self.model.__name__} not found.")
        await self.post_delete(result)
        return result

    async def delete_multi(self, ids: list[Any]) -> Sequence[ModelType]:
        await self.pre_delete_multi(ids)
        result = await self.repository.delete_multi(ids)
        await self.post_delete_multi(result)
        return result

class SearchServiceMixin(Generic[ModelType]):
    repository: BaseRepository
    model: Type[ModelType]

    async def pre_search(self, search_in: SearchRequest) -> None: pass
    async def post_search(self, models: Sequence[ModelType]) -> None: pass

    async def search(self, search_in: SearchRequest, pagination: Any = None) -> Any:
        await self.pre_search(search_in)
        result = await self.repository.search(search_in, pagination)
        if pagination is None:
            await self.post_search(result)
            return result
        await self.post_search(result.data)
        return result

class BaseService(
    Generic[ModelType, CreateSchemaType, UpdateSchemaType],
    ReadServiceMixin[ModelType],
    WriteServiceMixin[ModelType, CreateSchemaType, UpdateSchemaType],
    SearchServiceMixin[ModelType]
):
    def __init__(self, model: Type[ModelType], repository: BaseRepository):
        self.model = model
        self.repository = repository