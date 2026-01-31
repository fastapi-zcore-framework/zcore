from fastapi import Request

from starlette.middleware.base import BaseHTTPMiddleware

from app.core.context import set_current_user_id
from app.core.exception.exceptions import AppException

class SetUserContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if hasattr(request.state, "user"):
            set_current_user_id(request.state.user.id)
        try:
            return await call_next(request)
        except Exception as e:
            raise AppException(message="Internal error when tring to set user context.")