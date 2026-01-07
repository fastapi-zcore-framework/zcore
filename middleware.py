import uuid
import structlog
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

log = structlog.get_logger()

class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        s_time = time.perf_counter()
        structlog.contextvars.clear_contextvars()
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(
            request_id=request_id
        )
        
        try:
            response = await call_next(request)
            duration = (time.perf_counter() - s_time) * 1000
            
            log.info(
                "http request",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration, 2),
                client_ip=request.client.host if request.client else None,
            )
            response.headers["X-Request-ID"] = request_id
            
            return response
        
        except Exception:
            duration = (time.perf_counter() - s_time) * 1000
            log.exception(
                "http request failed",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration, 2),
            )
            raise