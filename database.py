from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engin = create_async_engine(settings.DATABASE_URL, echo=True)

SessionLocal = async_sessionmaker(engin)

class Base(DeclarativeBase):
    pass

async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()