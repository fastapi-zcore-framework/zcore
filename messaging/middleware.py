import asyncio

from fastapi import Request

from starlette.middleware.base import BaseHTTPMiddleware

from app.core.context import get_current_user_id
from app.core.messaging.service import outbox_process

class OutboxProcessorMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        user_id = get_current_user_id()
        if 200 <= response.status_code < 300 and user_id:
            asyncio.create_task(outbox_process(user_id))
        return response