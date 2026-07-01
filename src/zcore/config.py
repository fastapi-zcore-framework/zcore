import os
from typing import Any, Type, TypeVar, cast
from pydantic_settings import BaseSettings, SettingsConfigDict
from zcore.kernel.di import container

T = TypeVar("T", bound="ZCoreCoreSettings")

class ZCoreCoreSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_FILE", ".env"),
        extra="ignore",
        case_sensitive=True
    )

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
    REDIS_URL: str | None = None
    ENVIRONMENT: str = "production"

def initialize_settings(settings_inst: ZCoreCoreSettings) -> None:
    container.register_singleton(settings_inst.__class__, settings_inst)
    if settings_inst.__class__ is not ZCoreCoreSettings:
        container.register_singleton(ZCoreCoreSettings, settings_inst)

def get_settings(settings_class: Type[T] = ZCoreCoreSettings) -> T:
    try:
        return cast(T, container.resolve(settings_class))
    except Exception:
        settings_inst = settings_class()
        initialize_settings(settings_inst)
        return cast(T, settings_inst)

class SettingsProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_settings(), name)

settings = SettingsProxy()