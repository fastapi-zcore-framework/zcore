from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel, Field

T = TypeVar("T")

class ResponseWrapper(BaseModel, Generic[T]):
    success: bool = True
    message: str = "Success"
    data: Optional[T] = None
    meta: Optional[dict[str, Any]] = None

    # Helper method for consistent creation
    @classmethod
    def success_response(cls, data: T, message: str = "Success", meta: dict = None):
        return cls(success=True, message=message, data=data, meta=meta)