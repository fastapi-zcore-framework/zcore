import uuid

from sqlalchemy import select
from typing import Sequence

from app.core.utils import SessionDep
from app.core.messaging.models import OutboxEvent, Status
from app.core.messaging.schemas import OutboxEventCreate, OutboxEventUpdate
from app.core.repository import BaseRepository

class OutboxRepository(BaseRepository[OutboxEvent, OutboxEventCreate, OutboxEventUpdate]):
    def __init__(self, db:SessionDep):
        super().__init__(OutboxEvent, db)
        
    async def get_by_user_id(self, user_id: uuid.UUID) -> Sequence[OutboxEvent]:
        result = await self.db.execute(select(self.model).where(self.model.user_id == user_id, self.model.status == Status.Pending))
        events = result.scalars().all()
        return events