import uuid
from typing import Protocol, runtime_checkable
from datetime import datetime

@runtime_checkable
class UserProtocol(Protocol):
    id: uuid.UUID
    is_active: bool
    is_superuser: bool
    is_staff: bool
    
    last_login: datetime
    created_at: datetime
    
    @property
    def all_scopes(self) -> set[str]:
        ...