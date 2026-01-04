class AppException(Exception):
    def __init__(self, message: str, payload: dict = None):
        super().__init__(message)
        self.message = message
        self.payload = payload

class EntityNotFound(AppException):
    pass

class DuplicateEntity(AppException):
    pass

class AuthError(AppException):
    pass

class ValidationError(AppException):
    pass