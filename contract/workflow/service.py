import uuid

from typing import Protocol, Optional
from app.modules.workflow.models import Services

class ServiceValidator(Protocol):       
    async def get(self, id: uuid.UUID) -> Optional[Services]:
        ...