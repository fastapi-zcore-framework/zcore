import uuid
from typing import Protocol, Optional, Any

from app.core.db.pagination import PaginatedResult


class UserValidator(Protocol):
    async def get(self, id: uuid.UUID) -> Optional[Any]: ...

    async def get_active_paginated(self, params: Any) -> PaginatedResult: ...