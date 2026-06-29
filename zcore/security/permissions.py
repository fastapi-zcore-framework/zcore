from fastapi import Request, Depends
from typing import Annotated

from zcore.exceptions.base import ForbiddenError, AuthError
from zcore.security.protocols import UserProtocol

from app.modules.auth.dependencies import get_current_user

class PermissionChecker:
    def __init__(self, required_scopes: list[str]):
        self.required_scopes = required_scopes
        
    async def __call__(self, request: Request, user: Annotated[UserProtocol, Depends(get_current_user)]): 
        if not user:
            raise AuthError(message="Authentication required")
        
        if user.is_superuser:
            return user
        
        user_scopes = getattr(user, "all_scopes", set())
        if not set(self.required_scopes).issubset(user_scopes):
            raise ForbiddenError(message=f"Missing permissions: {self.required_scopes}")
        
        if not user.is_active:
            raise AuthError(message="User is inactive")

        request.state.user = user
        request.state.action_scope = self.required_scopes
        return user

    @classmethod
    def required(cls, *permissions: str) -> Depends:
        return Depends(cls(list(permissions)))