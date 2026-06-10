from typing import Generic ,TypeVar, Type, Any, Sequence, Optional
from pydantic import BaseModel
from sqlalchemy import select, inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.interfaces import ExecutableOption

from app.core.db.setup import Base
from app.core.db.search import SearchRequest, SearchEngine

from app.core.db.pagination import (
    PaginatedResult, 
    BasePagination,
    PageNumberPagination, 
    CursorPagination, 
    PageNumberParams, 
    CursorParams
)

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Base Repository with default CRUD operations.
    """
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        """
        :param model: The SQLAlchemy model class (e.g., Users)
        :param db: The AsyncSession dependency
        """
        self.model = model
        self.db = db
        
        self.pk = inspect(self.model).primary_key[0]
        self.cursor_field = self.pk.name
        
    async def paginate(self, params: Any) -> PaginatedResult[ModelType]:
        query = select(self.model)
        
        if isinstance(params, CursorParams):
            paginator = CursorPagination(cursor_field=self.cursor_field)
        else:
            paginator = PageNumberPagination()
            
        return await paginator.paginate(
            session=self.db,
            query=query,
            params=params,
            model=self.model
        )
    
    async def search_paginated(
        self, 
        search_in: SearchRequest, 
        pagination_class: Optional[Type[BasePagination]] = None
    ) -> PaginatedResult[ModelType]:
        
        use_cursor = False
        if pagination_class is not None:
            use_cursor = issubclass(pagination_class, CursorPagination)
        else:
            use_cursor = search_in.cursor is not None

        if use_cursor:
            params = CursorParams(
                cursor=search_in.cursor,
                size=search_in.size
            )
            paginator = CursorPagination(cursor_field=self.cursor_field)
        else:
            params = PageNumberParams(
                page=search_in.page or 1,
                size=search_in.size
            )
            paginator = PageNumberPagination()

        engine = SearchEngine(self.model)
        engine._validate_request(search_in)
        query = engine.build_base_query(search_in)
        
        return await paginator.paginate(
            session=self.db,
            query=query,
            params=params,
            model=self.model
        )
    
    async def get(self, id: Any, options: list[ExecutableOption] = None) -> Optional[ModelType]:
        """Get a single record by ID."""
        query = select(self.model).where(self.pk == id)
        if options:
            if isinstance(options, list):
                query = query.options(*options)
            else:
                query = query.options(options)
        result = await self.db.execute(query)
        record = result.scalars().first()
        return record
    
    async def bulk_get(self, ids: list[Any], options: list[ExecutableOption] = None) -> Sequence[ModelType]:
        """Get list of records by ids."""
        query = select(self.model).where(self.pk.in_(ids))
        if options:
            if isinstance(options, list):
                query = query.options(*options)
            else:
                query = query.options(options)
        result = await self.db.execute(query)
        record = result.scalars().all()
        return record
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> Sequence[ModelType]:
        """Get all record with pagination."""
        result = await self.db.execute(select(self.model).offset(skip).limit(limit))
        records = result.scalars().all()
        return records
    
    async def search(self, search_in: SearchRequest) -> Sequence[ModelType]:
        engine = SearchEngine(self.model)
        query = engine.build_query(search_in)
        
        result = await self.db.execute(query)
        return result.scalars().all()
     
    async def create(self, schema: CreateSchemaType, auto_commit: bool = True) -> ModelType:
        """Create a new record."""
        new_record = self.model(**schema.model_dump())

        self.db.add(new_record)
        if auto_commit:
            await self.db.commit()
            await self.db.refresh(new_record)
        else:
            await self.db.flush() 
        
        return new_record
    
    async def update(self, id:Any, schema: UpdateSchemaType, auto_commit: bool = True) -> Optional[ModelType]:
        """Update an existing record by ID."""
        
        record = await self.get(id)
        if not record:
            return None 
        
        update_data = schema.model_dump(exclude_unset=False)

        for field, value in update_data.items():
            setattr(record, field, value)

        if auto_commit:
            await self.db.commit()
            await self.db.refresh(record)
        else:
            await self.db.flush() 
        
        return record
    
    async def patch(self, id:Any, schema: UpdateSchemaType, auto_commit: bool = True) -> Optional[ModelType]:
        """Update an existing record by ID."""
        
        record = await self.get(id)
        if not record:
            return None 
        
        update_data = schema.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(record, field, value)

        if auto_commit:
            await self.db.commit()
            await self.db.refresh(record)
        else:
            await self.db.flush() 
        
        return record
    
    async def delete(self, id: Any, auto_commit: bool = True) -> ModelType | None:
        """Delete a record by ID."""
        
        record = await self.get(id)
        if not record:
            return None
        
        await self.db.delete(record)
        
        if auto_commit:
            await self.db.commit()
        else:
            await self.db.flush() 
        
        return record
    
    async def commit(self):
        await self.db.commit()

    async def rollback(self):
        await self.db.rollback()

    async def refresh(self, instance: Any):
        await self.db.refresh(instance)
        
    async def flush(self):
        await self.db.flush()