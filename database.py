from dataclasses import dataclass
from functools import cached_property
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engin = create_async_engine(settings.DATABASE_URL, echo=True)

SessionLocal = async_sessionmaker(engin)

@dataclass(frozen=True)
class Actions:
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
            CREATE = f"{table}:create",
            UPDATE = f"{table}:update",
            DELETE = f"{table}:delete"
        )


async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()