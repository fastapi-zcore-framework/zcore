
import uuid

from typing import Protocol, Optional
from app.modules.workflow.models import Stages

class StageValidator(Protocol):       
    async def get(self, id: uuid.UUID) -> Optional[Stages]:
        ...