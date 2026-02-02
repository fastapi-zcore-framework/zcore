from jose import jwt, JWTError
from passlib.context import CryptContext
from datetime import datetime, timezone, timedelta

from app.core.auth.models import Users
from app.core.exception.exceptions import AuthError
from app.core.config import settings
    
pwd_context = CryptContext(schemes=['sha256_crypt'], deprecated='auto')

def verify_password(plain_password:str, hashed_password:str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password:str) -> str:
    return pwd_context.hash(password)

def create_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None

async def validate_token(repo, token:str, payload_type: str = "refresh") -> Users:
    payload = decode_token(token)
    if payload is None:
        raise AuthError(message="Invalid token format")
    
    if payload.get("type") != payload_type :
        raise AuthError(message="Invalid token type")

    if is_token_expired(payload.get("exp")):
        raise AuthError("Token expired")

    username = payload.get("sub", None)
    if not username:
        raise AuthError(message="Invalid token subject")
    
    user = await repo.get_by_username(username)
    
    if not user:
        raise AuthError(message="Invalid authentication credentials")
    
    return user
      
def is_token_expired(token_exp: int) -> bool:
    """
    Check if a JWT token has expired based on its 'exp' timestamp.

    Args:
        token_exp (int): The expiration time of the token as a Unix timestamp (seconds since epoch).

    Returns:
        bool: True if the token is expired or invalid, False if it is still valid.
    """
    
    if not token_exp:
        return True
    
    expire_time = datetime.fromtimestamp(token_exp, tz=timezone.utc)
    now = datetime.now(timezone.utc)
    
    return now >= expire_time