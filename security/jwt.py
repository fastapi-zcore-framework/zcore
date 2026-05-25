from datetime import datetime, timezone, timedelta
from jose import jwt, JWTError
from app.core.config import settings
from app.core.exception.exceptions import AuthError

def create_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise AuthError(message="Invalid or expired token")
    
def is_token_expired(token_exp: int) -> bool:   
    if not token_exp:
        return True
    
    expire_time = datetime.fromtimestamp(token_exp, tz=timezone.utc)
    now = datetime.now(timezone.utc)
    
    return now >= expire_time