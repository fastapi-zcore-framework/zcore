import uuid

from typing import Protocol, Optional
from app.modules.crm.models import Doctors

class DoctorValidator(Protocol):       
    async def get(self, id: uuid.UUID) -> Optional[Doctors]:
        ...