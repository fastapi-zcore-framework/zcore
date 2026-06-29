from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    DATABASE_URL: str
    MAX_OVERFLOW: int
    POOL_SIZE: int
    DATABASE_TEST_URL: str
    SECRET_KEY: str
    PROJECT_NAME: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    STORAGE_PATH: str
        
settings = Settings()