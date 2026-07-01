import jwt
import structlog
from datetime import datetime, timezone, timedelta
from typing import Union

from zcore.config import settings
from zcore.exceptions.base import AuthError

logger = structlog.get_logger()

def _get_signing_keys() -> tuple[Union[str, bytes], Union[str, bytes], str]:
    """
    Intelligently resolves signing keys based on configuration.
    Supports Symmetric (HMAC) and Asymmetric (RSA/ECDSA) out-of-the-box.
    """
    # If Asymmetric keys are provided via settings
    private_key = getattr(settings, "JWT_PRIVATE_KEY", None)
    public_key = getattr(settings, "JWT_PUBLIC_KEY", None)
    
    if private_key and public_key:
        return private_key, public_key, settings.ALGORITHM
        
    # Default to Symmetric signing
    # Fast Startup Safeguard: Blow up if running in production with insecure fallback
    is_prod = getattr(settings, "ENVIRONMENT", "production").lower() == "production"
    is_fallback = settings.SECRET_KEY == "zcore-insecure-fallback-secret-key-must-be-changed"
    
    if is_prod and is_fallback:
        raise RuntimeError(
            "FATAL SECURITY VIOLATION: You are running in PRODUCTION environment "
            "using the insecure default fallback SECRET_KEY. Application startup aborted."
        )
        
    return settings.SECRET_KEY, settings.SECRET_KEY, settings.ALGORITHM

def create_token(data: dict, expires_delta: timedelta|None = None) -> str:
    """Creates a JWT access token using either symmetric or asymmetric signing."""
    private_key, _, algorithm = _get_signing_keys()
    to_encode = data.copy()
    
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    
    try:
        return jwt.encode(to_encode, private_key, algorithm=algorithm)
    except Exception as e:
        logger.error(f"Failed to encode JWT token: {e}")
        raise AuthError(message="Token creation failed due to internal error.")

def decode_token(token: str) -> dict:
    """Decodes and validates a JWT token using either symmetric or asymmetric verification."""
    _, public_key, algorithm = _get_signing_keys()
    try:
        return jwt.decode(token, public_key, algorithms=[algorithm])
    except jwt.ExpiredSignatureError as e:
        raise AuthError(message="Token expired") from e
    except jwt.InvalidTokenError as e:
        raise AuthError(message="Invalid token structure") from e
    
def is_token_expired(token_exp: int) -> bool:   
    if not token_exp:
        return True
    
    expire_time = datetime.fromtimestamp(token_exp, tz=timezone.utc)
    now = datetime.now(timezone.utc)
    
    return now >= expire_time