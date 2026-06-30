from typing import Any, Optional, Type, TypeVar, cast
from pydantic_settings import BaseSettings, SettingsConfigDict

T = TypeVar("T", bound="ZCoreCoreSettings")

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

_active_settings: Optional[ZCoreCoreSettings] = None

def set_settings(settings_inst: ZCoreCoreSettings) -> None:
    global _active_settings
    _active_settings = settings_inst

def get_settings(settings_class: Type[T] = ZCoreCoreSettings) -> T:
    global _active_settings
    if _active_settings is None:
        _active_settings = settings_class()
    return cast(T, _active_settings)

class SettingsProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_settings(), name)

settings = SettingsProxy()