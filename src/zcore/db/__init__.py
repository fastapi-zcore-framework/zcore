from zcore.db.setup import Base, db_manager, get_db, SessionDep
from zcore.db.repository import BaseRepository, AbstractRepository
from zcore.db.uow import UnitOfWork
from zcore.db.pagination import (
    PaginatedResult,
    BasePagination,
    PageNumberPagination,
    CursorPagination,
    PageNumberParams,
    CursorParams,
)
from zcore.db.search import SearchRequest, SearchEngine
from zcore.db.events import register_db_event_dispatcher, dispatch_db_event

__all__ = [
    "Base",
    "db_manager",
    "get_db",
    "BaseRepository",
    "AbstractRepository",
    "UnitOfWork",
    "PaginatedResult",
    "BasePagination",
    "PageNumberPagination",
    "CursorPagination",
    "PageNumberParams",
    "CursorParams",
    "SearchRequest",
    "SearchEngine",
    "register_db_event_dispatcher",
    "dispatch_db_event",
]