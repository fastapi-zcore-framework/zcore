from dataclasses import dataclass
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
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

async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()