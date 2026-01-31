import uuid

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, ConfigDict

from app.core.messaging.models import Status

class OutboxEventCreate(BaseModel):
    aggregate_type: str
    aggregate_id: uuid.UUID
    event_type: str
    payload: dict[str, Any]
    before_state: dict[str, Any] | None = None
    status: Status
    
class OutboxEventUpdate(BaseModel):
    status: Status
    processed_at: datetime
    retry_count: int | None = None

class OutboxEventPublic(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    
    aggregate_type: str
    aggregate_id: uuid.UUID
    
    event_type: str
    
    payload: dict[str, Any]
    before_state: dict[str, Any] | None = None
    
    status: Status
    
    created_at: datetime
    processed_at: datetime
    
    retry_count: int
    
    model_config = ConfigDict(from_attributes=True)