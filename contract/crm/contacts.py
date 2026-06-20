from typing import Protocol, Any

from app.modules.crm.models import Contacts
from app.modules.crm.schemas import ContactCreate, ContactUpdate

class Contacts(Protocol):       
    async def create(self, schema: ContactCreate) -> Contacts:
        ...
    
    async def update(self, id: Any, schema: ContactUpdate, partial: bool = False) -> Contacts:
        ...