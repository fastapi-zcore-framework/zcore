from typing import Any, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class ZCoreCoreSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "sqlite+aiosqlite:///zcore.db"
    MAX_OVERFLOW: int = 10
    POOL_SIZE: int = 5
    DATABASE_TEST_URL: str = "sqlite+aiosqlite:///zcore_test.db"
    
    SECRET_KEY: str = "zcore-insecure-fallback-secret-key-must-be-changed"
    PROJECT_NAME: str = "ZCore Enterprise Application"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    STORAGE_PATH: str = "./storage"
    REDIS_URL: Optional[str] = None

_active_settings: Any = None

def set_settings(settings_inst: Any) -> None:
    global _active_settings
    _active_settings = settings_inst

def get_settings() -> Any:
    global _active_settings
    if _active_settings is None:
        _active_settings = ZCoreCoreSettings()
    return _active_settings

class SettingsProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_settings(), name)

settings = SettingsProxy()