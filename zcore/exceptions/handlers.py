import structlog
from fastapi import Request
from fastapi.responses import JSONResponse

from zcore.exceptions.base import AppException
from zcore.web.response import ResponseWrapper

log = structlog.get_logger()

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    log.warning(
        "AppException raised",
        type=type(exc).__name__,
        status_code=exc.status_code,
        message=exc.message,
        payload=exc.payload,
        path=request.url.path,
        method=request.method
    )
    
    response_payload = ResponseWrapper[None](
        success=False,
        message=exc.message,
        data=None,
        meta={
            "error_type": exc.__class__.__name__,
            "payload": exc.payload
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_payload.model_dump()
    )