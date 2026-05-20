import uuid

from typing import Protocol, Optional
from app.modules.personnel.models import UserHRProfile
from app.modules.personnel.schemas import UserHRProfileCreate


class HRProfileContract(Protocol):       
    async def get(self, id: uuid.UUID) -> Optional[UserHRProfile]:
        ...
        
    async def create(self, schema:UserHRProfileCreate, auto_commit: bool = True) -> UserHRProfile:
        ...