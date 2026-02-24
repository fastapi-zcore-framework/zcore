import uuid

from datetime import datetime
from app.core.database import db_manager
from app.core.messaging.sse import stream_manager
from app.core.messaging.models import Status
from app.core.messaging.schemas import OutboxEventUpdate, OutboxEventPublic
from app.core.messaging.repository import OutboxRepository

async def outbox_process(user_id: uuid.UUID):
    async with db_manager.session() as session:
        repo = OutboxRepository(session)
        
        events = await repo.get_by_user_id(user_id)
    
        for event in events:
            schema = OutboxEventUpdate(
                status= Status.Processed,
                processed_at= datetime.now(),
                retry_count= event.retry_count + 1
            )
            event = await repo.update(event.id, schema)
            
            event_data = OutboxEventPublic.model_validate(event).model_dump(mode='json')
            await stream_manager.publish(user_id, data=event_data)