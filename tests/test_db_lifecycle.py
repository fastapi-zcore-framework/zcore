import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Type
from unittest.mock import AsyncMock, MagicMock
import pytest

from zcore.db.setup import DatabaseManager
from zcore.db.uow import UnitOfWork
from zcore.kernel.events import EventDispatcher

@pytest.mark.parametrize(
    "db_url, pool_size, max_overflow",
    [
        ("sqlite+aiosqlite:///:memory:", 5, 10),
        ("sqlite+aiosqlite:///:memory:", 10, 20),
    ]
)
@pytest.mark.anyio
async def test_db_manager_init(db_url: str, pool_size: int, max_overflow: int) -> None:
    manager = DatabaseManager()
    manager.init_app(
        db_url=db_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        echo=False
    )
    
    assert manager._engine is not None
    assert manager._session_factory is not None
    
    await manager.close()

@pytest.mark.parametrize(
    "exception_class",
    [
        ValueError,
        RuntimeError,
        TypeError,
    ]
)
@pytest.mark.anyio
async def test_db_session_rollback_on_error(exception_class: Type[Exception]) -> None:
    manager = DatabaseManager()
    mock_session = AsyncMock()
    
    @asynccontextmanager
    async def mock_session_ctx() -> AsyncGenerator[AsyncMock, None]:
        yield mock_session

    manager._session_factory = mock_session_ctx

    with pytest.raises(exception_class):
        async with manager.session() as session:
            assert session is mock_session
            raise exception_class("Simulated database error")

    mock_session.rollback.assert_called_once()

@pytest.mark.parametrize(
    "events_to_register",
    [
        [("user.created", {"id": str(uuid.uuid4())})],
        [
            ("order.created", {"id": str(uuid.uuid4())}),
            ("inventory.decremented", {"sku": "SKU-123", "qty": 1})
        ],
        []
    ]
)
@pytest.mark.anyio
async def test_uow_commit_emits_events(events_to_register: list[tuple[str, dict[str, Any]]]) -> None:
    session = AsyncMock()
    dispatcher = AsyncMock()
    uow = UnitOfWork(session, dispatcher)
    
    call_order: list[str] = []
    
    async def track_commit() -> None:
        call_order.append("commit")
        
    async def track_dispatch(event: str, payload: Any) -> list[Any]:
        call_order.append(f"dispatch:{event}")
        return []

    session.commit.side_effect = track_commit
    dispatcher.dispatch.side_effect = track_dispatch

    for event_name, payload in events_to_register:
        uow.register_event(event_name, payload)

    await uow.commit()

    if events_to_register:
        assert call_order[0] == "commit"
        for i, (event_name, _) in enumerate(events_to_register):
            assert call_order[i + 1] == f"dispatch:{event_name}"
    else:
        assert call_order == ["commit"]

@pytest.mark.parametrize(
    "exception_class, events_to_register",
    [
        (ValueError, [("payment.failed", {"amount": 100})]),
        (RuntimeError, [("log.error", {"msg": "failure"}), ("alert.sent", {})]),
    ]
)
@pytest.mark.anyio
async def test_uow_rollback_clears_events(
    exception_class: Type[Exception],
    events_to_register: list[tuple[str, dict[str, Any]]]
) -> None:
    session = AsyncMock()
    session.info = {}
    dispatcher = AsyncMock()
    uow = UnitOfWork(session, dispatcher)

    for event_name, payload in events_to_register:
        uow.register_event(event_name, payload)

    await uow.rollback()
    assert len(uow._pending_events) == 0
    dispatcher.dispatch.assert_not_called()

    for event_name, payload in events_to_register:
        uow.register_event(event_name, payload)

    with pytest.raises(exception_class):
        async with uow:
            raise exception_class("Simulated processing error")

    assert len(uow._pending_events) == 0
    dispatcher.dispatch.assert_not_called()
    session.rollback.assert_called()