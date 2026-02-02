from typing import Annotated
from fastapi import Depends, Request
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.auth.models import Users

from app.core.exception.exceptions import AuthError, ForbiddenError

from app.core.context import set_current_user_id

from app.core.auth.security import validate_token
from app.modules.auth.repository import UserRepository, RoleRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

UserRepoDep = Annotated[UserRepository, Depends()]
RoleRepoDep = Annotated[RoleRepository, Depends()]

async def get_current_user(repo: UserRepoDep, token:str = Depends(oauth2_scheme)) -> Users:
    user: Users = await validate_token(repo, token, "access")
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    set_current_user_id(user.id)
    return user

UserDep = Annotated[Users, Depends(get_current_user)]

class PermissionChecker:
    def __init__(self, required_scopes:list[str]):
        self.required_scopes = required_scopes
        
    async def __call__(self, request: Request, user: UserDep):       
        # if user is superuser accept it
        if user.is_superuser:
            return user
        
        # check all required scope for user
        if not set(self.required_scopes).issubset(user.all_scopes):
            raise ForbiddenError(
                message=f"Not enough permissions. Required : {self.required_scopes}"
            )
        
        if not user.is_active:
            raise AuthError(
                message="Invalid user."
            )
        
        request.state.user = user
        request.state.action_scope = self.required_scopes
        
        return user
                
    @classmethod
    def required(cls, *permissions: str) -> Depends:
        return Depends(cls(list(permissions)))