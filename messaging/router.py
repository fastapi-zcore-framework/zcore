import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.core.messaging.sse import stream_manager
from app.core.auth.dependencies import UserDep

router = APIRouter()

@router.get(
    path="/stream/notifications"
)
async def notifications(user: UserDep):
    async def event_generator():
        queue = stream_manager.subscribe(user.id)
        try:
            while True:
                data = await queue.get()
                yield f"data: {json.dumps(data)}\n\n"
        finally:
            await stream_manager.unsubscribe(user.id, queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")