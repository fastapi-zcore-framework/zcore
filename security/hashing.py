from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

try:
    from argon2.exceptions import InvalidHashError
except ImportError:
    from argon2.exceptions import InvalidHash as InvalidHashError

ph = PasswordHasher()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, InvalidHashError):
        return False

def get_password_hash(password: str) -> str:
    return ph.hash(password)