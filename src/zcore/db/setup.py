import structlog
from fastapi import Depends
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncGenerator, Any, Optional, Annotated
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession, AsyncEngine
from sqlalchemy.orm import DeclarativeBase

logger = structlog.get_logger()

@dataclass(frozen=True)
class Actions:
    LISTVIEW: str
    VIEW: str
    CREATE: str
    UPDATE: str
    DELETE: str

    @classmethod
    def actions(cls, t_name: str) -> "Actions":
        actions = {}
        for action in cls.__dataclass_fields__.keys():
            actions[action] = f"{t_name}:{action.lower()}"
        return cls(**actions)

class Base(DeclarativeBase):
    @classmethod
    def actions(cls) -> Actions:
        t_name = getattr(cls, "__tablename__", None)
        if not t_name:
            raise AttributeError(f"Model {cls.__name__} does not have a __tablename__ defined.")
        return Actions.actions(t_name)

class DatabaseManager:
    def __init__(self) -> None:
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None

    def init_app(
        self, 
        db_url: str, 
        pool_size: int = 5, 
        max_overflow: int = 10, 
        pool_recycle: int = 1800, 
        echo: bool = False,
        **engine_kwargs: Any
    ) -> None:
        kwargs: dict[str, Any] = {}
        if "sqlite" not in db_url:
            kwargs["pool_size"] = pool_size
            kwargs["max_overflow"] = max_overflow
            kwargs["pool_recycle"] = pool_recycle

        self._engine = create_async_engine(
            db_url,
            echo=echo,
            pool_pre_ping=True,
            **kwargs,
            **engine_kwargs
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        logger.info("DatabaseManager successfully initialized.")

    async def close(self) -> None:
        if self._engine:
            await self._engine.dispose()
            logger.info("DatabaseManager engine connections closed.")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        if not self._session_factory:
            raise RuntimeError("DatabaseManager has not been initialized. Call init_app() first.")
            
        async with self._session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

db_manager = DatabaseManager()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with db_manager.session() as session:
        yield session
        
SessionDep = Annotated[AsyncSession, Depends(get_db)]