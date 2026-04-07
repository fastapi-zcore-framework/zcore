import uuid

from typing import Protocol, Optional
from app.modules.crm.models import Patients

class PatientValidator(Protocol):       
    async def get(self, id: uuid.UUID) -> Optional[Patients]:
        ...