from fastapi import Request, Depends
from app.core.exception.exceptions import ForbiddenError, AuthError
from app.core.db.protocols import UserProtocol

class PermissionChecker:
    def __init__(self, required_scopes: list[str]):
        self.required_scopes = required_scopes
        
    async def __call__(self, request: Request, user: UserProtocol): 
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