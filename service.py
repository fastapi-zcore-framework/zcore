from typing import Generic ,TypeVar, Type, Any, Sequence, Optional
from pydantic import BaseModel

from app.core.repository import BaseRepository
from app.core.exception.exceptions import EntityNotFound
from app.core.database import Base
 
ModelType = TypeVar("ModelType", bound=Base)        
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType], repository: BaseRepository):
        self.model = model
        self.repository = repository
    
    async def pre_create(self, schema: CreateSchemaType) -> None: pass
    async def post_create(self, model: ModelType) -> None: pass
    
    async def pre_update(self, id: Any, schema: UpdateSchemaType) -> None: pass
    async def post_update(self, model: ModelType) -> None: pass
    
    async def pre_delete(self, id: Any) -> None: pass
    async def post_delete(self, id: Any) -> None: pass
    
    async def post_get(self, model: ModelType) -> ModelType: return model
    async def post_get_all(self, models: Sequence[ModelType]) -> Sequence[ModelType]: return models   
       
    async def create(self, schema: CreateSchemaType) -> ModelType:
        await self.pre_create(schema=schema)
        result = await self.repository.create(schema=schema)
        await self.post_create(model=result)
        return result
    
    async def get(self, id: Any) -> Optional[ModelType]:
        result = await self.repository.get(id=id)
        if not result:
            raise EntityNotFound(message=f"{self.model.__name__} not found.")
        result = await self.post_get(model=result)
        return result
    
    async def get_all(self, limit: int = 100, skip: int = 0) -> Sequence[ModelType]:
        result = await self.repository.get_all(skip=skip, limit=limit)
        result = await self.post_get_all(models=result)
        return result
    
    async def update(self, id: Any, schema: UpdateSchemaType) -> Optional[ModelType]:
        await self.pre_update(id=id, schema=schema)
        result = await self.repository.update(id=id, schema=schema)
        if not result:
            raise EntityNotFound(message=f"{self.model.__name__} not found.")
        await self.post_update(model=result)
        return result
    
    async def delete(self, id: Any) -> Optional[ModelType]:
        await self.pre_delete(id=id)
        result = await self.repository.delete(id=id)
        if not result:
            raise EntityNotFound(message=f"{self.model.__name__} not found.")
        await self.post_delete(id=id)
        return result