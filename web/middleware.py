import uuid
import time
import structlog
from starlette.types import ASGIApp, Scope, Receive, Send

log = structlog.get_logger()

class RequestLogMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        s_time = time.perf_counter()
        structlog.contextvars.clear_contextvars()
        
        headers = dict(scope.get("headers", []))
        request_id = headers.get(b"x-request-id", b"").decode() or str(uuid.uuid4())
        
        structlog.contextvars.bind_contextvars(request_id=request_id)

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"X-Request-ID", request_id.encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
            duration = (time.perf_counter() - s_time) * 1000
            
            log.info(
                "http request",
                method=scope.get("method"),
                path=scope.get("path"),
                duration_ms=round(duration, 2),
            )
        except Exception:
            duration = (time.perf_counter() - s_time) * 1000
            log.exception(
                "http request failed",
                method=scope.get("method"),
                path=scope.get("path"),
                duration_ms=round(duration, 2),
            )
            raise