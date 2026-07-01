import structlog
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

try:
    from argon2.exceptions import InvalidHashError
except ImportError:
    from argon2.exceptions import InvalidHash as InvalidHashError

from zcore.config import settings

logger = structlog.get_logger()

# Dynamically construct Argon2 parameters from config settings with safe fallbacks
_memory_cost = getattr(settings, "ARGON2_MEMORY_COST", 65536)     # 64 MB
_time_cost = getattr(settings, "ARGON2_TIME_COST", 3)             # 3 iterations
_parallelism = getattr(settings, "ARGON2_PARALLELISM", 4)         # 4 threads

ph = PasswordHasher(
    memory_cost=_memory_cost,
    time_cost=_time_cost,
    parallelism=_parallelism
)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Safely verifies a candidate password against an Argon2 hash."""
    try:
        return ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, InvalidHashError):
        return False
    except Exception as e:
        logger.error(f"Password verification encountered an unexpected failure: {e}")
        return False

def get_password_hash(password: str) -> str:
    """Generates an Argon2 secure hash for the provided password."""
    try:
        return ph.hash(password)
    except Exception as e:
        logger.error(f"Password hashing failed: {e}")
        raise RuntimeError("Cryptographic error while processing password.")