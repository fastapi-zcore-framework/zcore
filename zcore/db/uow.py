import logging
from typing import Any, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from zcore.kernel.events import EventDispatcher

logger = logging.get_logger()

class UnitOfWork:
    def __init__(self, session: AsyncSession, dispatcher: EventDispatcher) -> None:
        self.session = session
        self.dispatcher = dispatcher
        self._pending_events: List[Tuple[str, Any]] = []

    def register_event(self, event_name: str, payload: Any) -> None:
        self._pending_events.append((event_name, payload))

    async def commit(self) -> None:
        """
        Commits the database session. If the commit fails, it raises the original exception.
        Only dispatches registered domain events AFTER a successful database commit.
        """
        try:
            await self.session.commit()
        except Exception as e:
            logger.error(f"Transaction commit failed in UnitOfWork: {e}")
            await self.session.rollback()
            raise

        # Dispatch events safely after a guaranteed commit
        while self._pending_events:
            event_name, payload = self._pending_events.pop(0)
            try:
                await self.dispatcher.dispatch(event_name, payload)
            except Exception as ex:
                logger.error(
                    f"UnitOfWork event handler failed for event '{event_name}': {ex}", 
                    exc_info=True
                )

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