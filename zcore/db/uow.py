from typing import Any, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from zcore.kernel.events import EventDispatcher

class UnitOfWork:
    def __init__(self, session: AsyncSession, dispatcher: EventDispatcher) -> None:
        self.session = session
        self.dispatcher = dispatcher
        self._pending_events: List[Tuple[str, Any]] = []

    def register_event(self, event_name: str, payload: Any) -> None:
        self._pending_events.append((event_name, payload))

    async def commit(self) -> None:
        await self.session.commit()
        while self._pending_events:
            event_name, payload = self._pending_events.pop(0)
            try:
                await self.dispatcher.dispatch(event_name, payload)
            except Exception:
                pass

    async def rollback(self) -> None:
        await self.session.rollback()
        self._pending_events.clear()

    async def __aenter__(self) -> "UnitOfWork":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type:
            await self.rollback()
        else:
            await self.commit()