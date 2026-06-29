import structlog

from fastapi import Request
from fastapi.responses import JSONResponse
from zcore.exceptions.base import AppException

log = structlog.get_logger()

async def app_exception_handler(request: Request, exc: AppException):
    log.warning(
        "AppException raised",
        type=type(exc).__name__,
        status_code=exc.status_code,
        message=exc.message,
        payload=exc.payload,
        path=request.url.path,
        method=request.method
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.message,
            "type": exc.__class__.__name__,
            "payload": exc.payload
        }
    )