from typing import Generic ,TypeVar, Type, Any, Sequence, Optional
from pydantic import BaseModel
from sqlalchemy import select, inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.interfaces import ExecutableOption

from app.core.database import Base

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
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> Sequence[ModelType]:
        """Get all record with pagination."""
        result = await self.db.execute(select(self.model).offset(skip).limit(limit))
        records = result.scalars().all()
        return records
    
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
        