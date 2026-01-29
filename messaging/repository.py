from app.core.utils import SessionDep

from app.core.messaging.models import OutboxEvent
from app.core.messaging.schemas import OutboxEventCreate, OutboxEventUpdate
from app.core.repository import BaseRepository

class OutboxRepository(BaseRepository[OutboxEvent, OutboxEventCreate, OutboxEventUpdate]):
    def __init__(self, db:SessionDep):
        super().__init__(OutboxEvent, db)