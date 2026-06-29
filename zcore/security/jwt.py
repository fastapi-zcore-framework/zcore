import jwt
from datetime import datetime, timezone, timedelta

from zcore.config import settings
from zcore.exceptions.base import AuthError

def create_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise AuthError(message="Token expired")
    except jwt.InvalidTokenError:
        raise AuthError(message="Invalid token structure")
    
def is_token_expired(token_exp: int) -> bool:   
    if not token_exp:
        return True
    
    expire_time = datetime.fromtimestamp(token_exp, tz=timezone.utc)
    now = datetime.now(timezone.utc)
    
    return now >= expire_time