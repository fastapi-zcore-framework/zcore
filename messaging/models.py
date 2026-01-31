import uuid

from enum import Enum
from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import String, DateTime, Integer, ForeignKey, Boolean, func

from app.core.database import Base

class Status(str, Enum):
    Pending = "Pending"
    Processed = "Processed"
    Failed = "Failed"

class OutboxEvent(Base):
    __tablename__ = "outbox_event"
    
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    
    aggregate_type: Mapped[str] = mapped_column(String(255))
    aggregate_id: Mapped[uuid.UUID] = mapped_column()
    
    event_type: Mapped[str] = mapped_column(String(255))
    
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    before_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    status: Mapped[Status] = mapped_column(
        SQLEnum(Status,
                name="outbox_status",
                native_enum=True),
        nullable=False,
        default="Pending"
    )
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    

class NotificationType(str, Enum):
    Success = "Success"
    Info = "Info"
    Warning = "Warning"
    Error = "Error"
    Pending = "Pending"
 
class Notifications(Base):
    __tablename__ = "notifications"
    
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    
    title: Mapped[str] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(String(255))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))