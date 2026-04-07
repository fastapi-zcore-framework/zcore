import uuid

from typing import Protocol, Any, Optional
from app.modules.catalog.models import CatalogTypes

class CatalogTypeValidator(Protocol):
    async def validate_catalog_and_schema(self, catalog_type_id: uuid.UUID, meta_data: dict[str, Any]) -> None:
        ...
        
    async def get(self, id: uuid.UUID) -> Optional[CatalogTypes]:
        ...