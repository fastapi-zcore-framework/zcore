from abc import ABC, abstractmethod
from typing import Any
from fastapi import Request, Depends

from zcore.exceptions.base import ForbiddenError, AuthError
from zcore.security.protocols import UserProtocol
from zcore.security.dependencies import get_current_user_stub

class BasePermission(ABC):
    @abstractmethod
    async def has_permission(self, request: Request, user: UserProtocol) -> bool:
        pass

    async def has_object_permission(self, request: Request, user: UserProtocol, obj: Any) -> bool:
        return True

    async def __call__(
        self, 
        request: Request, 
        user: UserProtocol = Depends(get_current_user_stub)
    ) -> UserProtocol:
        if not user:
            raise AuthError(message="Authentication required")
        
        if not user.is_active:
            raise AuthError(message="User is inactive")
            
        if not await self.has_permission(request, user):
            raise ForbiddenError(message="Access denied")
            
        return user

class ScopePermission(BasePermission):
    def __init__(self, *required_scopes: str, allow_superuser: bool = True):
        self.required_scopes = set(required_scopes)
        self.allow_superuser = allow_superuser

    async def has_permission(self, request: Request, user: UserProtocol) -> bool:
        if self.allow_superuser and getattr(user, "is_superuser", False):
            return True
            
        user_scopes = getattr(user, "all_scopes", set())
        return self.required_scopes.issubset(user_scopes)