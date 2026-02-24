from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dataclasses import dataclass
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Session

from app.core.messaging.outbox_handler import handle_outbox_events
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=True)

SessionLocal = async_sessionmaker(engine)

event.listen(Session, "before_flush", handle_outbox_events)

@dataclass(frozen=True)
class Actions:
    LISTVIEW:str
    VIEW:str
    CREATE:str
    UPDATE:str
    DELETE:str

class Base(DeclarativeBase):
    @classmethod
    def action(cls) -> Actions:
        table = cls.__tablename__
        return Actions(
            VIEW = f"{table}:view",
            LISTVIEW = f"{table}:listview",
            CREATE = f"{table}:create",
            UPDATE = f"{table}:update",
            DELETE = f"{table}:delete"
        )

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
        event.listen(
            self._session_factory.sync_session_class,
            "before_flush",
            handle_outbox_events)
        
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
        
    async def get_db(self) -> AsyncGenerator[AsyncSession, None]: 
        async with self._session_factory() as session:
                yield session

db_manager = DatabaseManager(settings.DATABASE_URL)

async def get_db():
    async for session in db_manager.get_db():
        yield session
