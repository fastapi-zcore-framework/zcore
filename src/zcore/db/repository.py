from pydantic import BaseModel
from typing import TYPE_CHECKING, Generic, TypeVar, Type, Any, Sequence, Optional, List
from sqlalchemy import select, inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.interfaces import ExecutableOption
from sqlalchemy.orm import load_only

from zcore.db.setup import Base
from zcore.db.pagination import (
    PageNumberPagination, 
    CursorPagination, 
    CursorParams
)

if TYPE_CHECKING:
    from zcore.db.search import SearchRequest, SearchEngine

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class AbstractRepository(Generic[ModelType]):
    db: AsyncSession
    model: Type[ModelType]
    pk: Any
    pk_name: str
    cursor_field: str

    async def get(self, id: Any, fields: Optional[List[Any]] = None, options: Optional[List[ExecutableOption]] = None) -> Optional[ModelType]:
        raise NotImplementedError

    async def get_by_ids(self, ids: List[Any], fields: Optional[List[Any]] = None, options: Optional[List[ExecutableOption]] = None) -> Sequence[ModelType]:
        raise NotImplementedError

class ReadRepositoryMixin(AbstractRepository[ModelType]):
    async def exist(self, id: Any) -> bool:
        query = select(self.model.id).where(self.pk == id).limit(1)
        result = await self.db.execute(query)
        return result.first() is not None

    async def get(self, id: Any, fields: Optional[List[Any]] = None, options: Optional[List[ExecutableOption]] = None) -> Optional[ModelType]:
        query = select(self.model).where(self.pk == id)
        if fields:
            query = query.options(load_only(*fields))
        if options:
            query = query.options(*options) if isinstance(options, list) else query.options(options)
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_by_ids(self, ids: List[Any], fields: Optional[List[Any]] = None, options: Optional[List[ExecutableOption]] = None) -> Sequence[ModelType]:
        # Fast path: Skip DB hit if empty list passed
        if not ids:
            return []
            
        query = select(self.model).where(self.pk.in_(ids))
        if fields:
            query = query.options(load_only(*fields))
        if options:
            query = query.options(*options) if isinstance(options, list) else query.options(options)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_list(self, pagination: Any = None, fields: Optional[List[Any]] = None, options: Optional[List[ExecutableOption]] = None) -> Any:
        query = select(self.model)
        if fields:
            query = query.options(load_only(*fields))
        if options:
            query = query.options(*options) if isinstance(options, list) else query.options(options)
        
        if pagination is None:
            result = await self.db.execute(query)
            return result.scalars().all()
            
        paginator = CursorPagination(self.cursor_field) if isinstance(pagination, CursorParams) else PageNumberPagination()
        return await paginator.paginate(self.db, query, pagination, self.model)

class WriteRepositoryMixin(Generic[ModelType, CreateSchemaType, UpdateSchemaType], AbstractRepository[ModelType]):
    async def create(self, schema: CreateSchemaType) -> ModelType:
        record = self.model(**schema.model_dump())
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def create_multi(self, schemas: List[CreateSchemaType], refresh: bool = False) -> Sequence[ModelType]:
        if not schemas:
            return []
            
        records = [self.model(**schema.model_dump()) for schema in schemas]
        self.db.add_all(records)
        await self.db.flush()
        if refresh:
            for record in records:
                await self.db.refresh(record)
        return records

    async def update(self, id: Any, schema: UpdateSchemaType, partial: bool = False) -> Optional[ModelType]:
        record = await self.get(id)
        if not record:
            return None
        update_data = schema.model_dump(exclude_unset=partial)
        for field, value in update_data.items():
            setattr(record, field, value)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def update_multi(self, data: dict[Any, UpdateSchemaType], partial: bool = False, refresh: bool = False) -> Sequence[ModelType]:
        if not data:
            return []
            
        records = await self.get_by_ids(ids=list(data.keys()))
        record_map = {getattr(r, self.pk_name): r for r in records}
        updated_records = []
        for record_id, schema in data.items():
            record = record_map.get(record_id)
            if record:
                update_data = schema.model_dump(exclude_unset=partial)
                for field, value in update_data.items():
                    setattr(record, field, value)
                updated_records.append(record)
        await self.db.flush()
        if refresh:
            for record in updated_records:
                await self.db.refresh(record)
        return updated_records

    async def delete(self, id: Any) -> Optional[ModelType]:
        record = await self.get(id)
        if not record:
            return None
        await self.db.delete(record)
        await self.db.flush()
        return record

    async def delete_multi(self, ids: List[Any]) -> Sequence[ModelType]:
        if not ids:
            return []
            
        records = await self.get_by_ids(ids=ids)
        for record in records:
            await self.db.delete(record)
        await self.db.flush()
        return records

class SearchRepositoryMixin(AbstractRepository[ModelType]):
    async def search(self, search_in: "SearchRequest", pagination: Any = None) -> Any:
        from zcore.db.search import SearchEngine
        engine = SearchEngine(self.model)
        query = engine.build_base_query(search_in)
        if pagination is None:
            result = await self.db.execute(query)
            return result.scalars().all()
            
        paginator = CursorPagination(self.cursor_field) if isinstance(pagination, CursorParams) else PageNumberPagination()
        return await paginator.paginate(self.db, query, pagination, self.model)

class BaseRepository(
    Generic[ModelType, CreateSchemaType, UpdateSchemaType],
    ReadRepositoryMixin[ModelType],
    WriteRepositoryMixin[ModelType, CreateSchemaType, UpdateSchemaType],
    SearchRepositoryMixin[ModelType]
):
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db
        self.pk = inspect(self.model).primary_key[0]
        self.pk_name = self.pk.name
        self.cursor_field = self.pk_name