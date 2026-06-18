from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

@dataclass(frozen=True)
class Actions:
    LISTVIEW: str
    VIEW: str
    CREATE: str
    UPDATE: str
    DELETE: str

    @classmethod
    def actions(cls, t_name):
        actions = {}
        for action in cls.__dataclass_fields__.keys():
            actions[action] = f"{t_name}:{action.lower()}"
        return cls(**actions)

class Base(DeclarativeBase):
    @classmethod
    def actions(cls) -> Actions: 
        return Actions.actions(cls.__tablename__)

class DatabaseManager:
    def __init__(self, db_url: str):
        self._engine = create_async_engine(
            db_url,
            echo=False,
            pool_size=settings.POOL_SIZE,
            max_overflow=settings.MAX_OVERFLOW,
            pool_recycle=1800,
            pool_pre_ping=True
        )
        self._session_factory = async_sessionmaker(
            self._engine,
            expire_on_commit=False
        )
           
    async def close(self):
        await self._engine.dispose()
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

db_manager = DatabaseManager(settings.DATABASE_URL)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with db_manager.session() as session:
        yield session