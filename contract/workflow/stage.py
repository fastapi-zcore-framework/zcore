
import uuid

from typing import Protocol, Optional, Sequence
from sqlalchemy.orm.interfaces import ExecutableOption
from app.modules.workflow.models import Stages

class StageContract(Protocol):       
    async def get(self, id: uuid.UUID) -> Optional[Stages]:
        ...
    
    async def bulk_get(self, ids: list[uuid.UUID],  options: list[ExecutableOption] = None) -> Sequence[Stages]:
        ...