import uuid

from typing import Protocol, Optional
from app.core.auth.models import Users

class UserValidator(Protocol):
    async def get(self, id: uuid.UUID) -> Optional[Users]:
        ...