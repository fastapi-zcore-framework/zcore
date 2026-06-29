from typing import Optional

class AppException(Exception):
    status_code: int = 500
    
    def __init__(self, message: str, payload: Optional[dict] = None) -> None:
        super().__init__(message)
        self.message = message
        self.payload = payload

class EntityNotFound(AppException):
    status_code = 404

class DuplicateEntity(AppException):
    status_code = 409

class AuthError(AppException):
    status_code = 401

class ForbiddenError(AppException):
    status_code = 403

class ValidationError(AppException):
    status_code = 400