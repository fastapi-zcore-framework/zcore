import uuid
from typing import Protocol, runtime_checkable

@runtime_checkable
class UserProtocol(Protocol):
    id: uuid.UUID
    is_active: bool
    
    @property
    def all_scopes(self) -> set[str]:
        ...