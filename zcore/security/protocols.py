import uuid
from typing import Protocol, runtime_checkable

@runtime_checkable
class UserProtocol(Protocol):
    id: uuid.UUID
    is_active: bool
    is_superuser: bool
    
    @property
    def all_scopes(self) -> set[str]:
        ...