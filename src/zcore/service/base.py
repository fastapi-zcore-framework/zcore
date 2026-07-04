from pydantic import BaseModel
from typing import Generic, TypeVar, Type, Any, Sequence, Optional, List, Dict, TYPE_CHECKING
from sqlalchemy.orm.interfaces import ExecutableOption

from zcore.exceptions.base import EntityNotFound
from zcore.db.setup import Base
from zcore.db.search import SearchRequest

if TYPE_CHECKING:
    from zcore.db.repository import BaseRepository

ModelType = TypeVar("ModelType", bound=Base)        
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class AbstractService(Generic[ModelType]):
    repository: "BaseRepository"
    model: Type[ModelType]

    async def get(
        self, 
        id: Any, 
        fields: Optional[List[Any]] = None, 
        options: Optional[List[ExecutableOption]] = None
    ) -> ModelType:
        raise NotImplementedError

    async def get_by_ids(
        self, 
        ids: List[Any], 
        fields: Optional[List[Any]] = None, 
        options: Optional[List[ExecutableOption]] = None
    ) -> Sequence[ModelType]:
        raise NotImplementedError

class ReadServiceMixin(AbstractService[ModelType]):
    async def post_get(self, model: ModelType) -> ModelType:
        return model

    async def post_get_multi(self, models: Sequence[ModelType]) -> Sequence[ModelType]:
        return models

    async def exist(self, id: Any) -> bool:
        return await self.repository.exist(id)

    async def get(
        self, 
        id: Any, 
        fields: Optional[List[Any]] = None, 
        options: Optional[List[ExecutableOption]] = None
    ) -> ModelType:
        result = await self.repository.get(id, fields, options)
        if not result:
            raise EntityNotFound(message=f"{self.model.__name__} not found.")
        return await self.post_get(result)

    async def get_by_ids(
        self, 
        ids: List[Any], 
        fields: Optional[List[Any]] = None, 
        options: Optional[List[ExecutableOption]] = None
    ) -> Sequence[ModelType]:
        result = await self.repository.get_by_ids(ids, fields, options)
        return await self.post_get_multi(result)

    async def get_list(
        self, 
        pagination: Any = None, 
        fields: Optional[List[Any]] = None, 
        options: Optional[List[ExecutableOption]] = None
    ) -> Any:
        result = await self.repository.get_list(pagination, fields, options)
        if pagination is None:
            return await self.post_get_multi(result)
        result.data = await self.post_get_multi(result.data)
        return result

class WriteServiceMixin(Generic[ModelType, CreateSchemaType, UpdateSchemaType], AbstractService[ModelType]):
    async def pre_create(self, schema: CreateSchemaType) -> None: pass
    async def post_create(self, model: ModelType) -> None: pass
    
    async def pre_create_multi(self, schemas: List[CreateSchemaType]) -> None: pass
    async def post_create_multi(self, models: Sequence[ModelType]) -> None: pass

    async def pre_update(self, id: Any, schema: UpdateSchemaType, partial: bool) -> None: pass
    async def post_update(self, model: ModelType) -> None: pass
    
    async def pre_update_multi(self, data: Dict[Any, UpdateSchemaType], partial: bool) -> None: pass
    async def post_update_multi(self, models: Sequence[ModelType]) -> None: pass

    async def pre_delete(self, id: Any) -> None: pass
    async def post_delete(self, model: ModelType) -> None: pass
    
    async def pre_delete_multi(self, ids: List[Any]) -> None: pass
    async def post_delete_multi(self, models: Sequence[ModelType]) -> None: pass

    async def _safe_commit(self) -> None:
        """
        Intelligently commits the active transaction only if the session is NOT managed
        by an outer UnitOfWork context. Prevents early-commit bugs in atomic operations.
        """
        session_info = self.repository.db.info
        if not session_info.get("uow_managed", False):
            try:
                await self.repository.db.commit()
            except Exception:
                await self.repository.db.rollback()
                raise

    async def create(self, schema: CreateSchemaType) -> ModelType:
        await self.pre_create(schema)
        result = await self.repository.create(schema)
        await self.post_create(result)
        await self._safe_commit()
        return result

    async def create_multi(self, schemas: List[CreateSchemaType], refresh: bool = False) -> Sequence[ModelType]:
        await self.pre_create_multi(schemas)
        result = await self.repository.create_multi(schemas, refresh=refresh)
        await self.post_create_multi(result)
        await self._safe_commit()
        return result

    async def update(self, id: Any, schema: UpdateSchemaType, partial: bool = False) -> ModelType:
        await self.pre_update(id, schema, partial)
        result = await self.repository.update(id, schema, partial)
        if not result:
            raise EntityNotFound(message=f"{self.model.__name__} not found.")
        await self.post_update(result)
        await self._safe_commit()
        return result

    async def update_multi(self, data: Dict[Any, UpdateSchemaType], partial: bool = False, refresh: bool = False) -> Sequence[ModelType]:
        await self.pre_update_multi(data, partial)
        result = await self.repository.update_multi(data, partial, refresh=refresh)
        await self.post_update_multi(result)
        await self._safe_commit()
        return result

    async def delete(self, id: Any) -> ModelType:
        await self.pre_delete(id)
        result = await self.repository.delete(id)
        if not result:
            raise EntityNotFound(message=f"{self.model.__name__} not found.")
        await self.post_delete(result)
        await self._safe_commit()
        return result

    async def delete_multi(self, ids: List[Any]) -> Sequence[ModelType]:
        await self.pre_delete_multi(ids)
        result = await self.repository.delete_multi(ids)
        await self.post_delete_multi(result)
        await self._safe_commit()
        return result

class SearchServiceMixin(AbstractService[ModelType]):
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
    def __init__(self, model: Type[ModelType], repository: "BaseRepository") -> None:
        self.model = model
        self.repository = repository