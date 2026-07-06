import datetime
import uuid
from typing import Any, AsyncGenerator, Type
import pytest
import pytest_asyncio
from sqlalchemy import Column, DateTime, Integer, String, select

from zcore.db.pagination import (
    CursorPagination,
    CursorParams,
    PageNumberPagination,
    PageNumberParams,
)
from zcore.db.setup import Base
from zcore.exceptions.base import ValidationError

class PaginationTestModel(Base):
    __tablename__ = f"pagination_test_{uuid.uuid4().hex[:6]}"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    created_at = Column(DateTime)

@pytest_asyncio.fixture(autouse=True)
async def setup_pagination_tables(test_engine: Any) -> AsyncGenerator[None, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.anyio
@pytest.mark.parametrize(
    "include_count, expected_total, expected_pages",
    [
        (True, 25, 2),
        (False, None, None),
    ]
)
async def test_page_number_pagination(
    db_session: Any,
    include_count: bool,
    expected_total: int | None,
    expected_pages: int | None
) -> None:
    records = [
        PaginationTestModel(id=i, name=f"Item {i}", created_at=datetime.datetime.now())
        for i in range(1, 26)
    ]
    db_session.add_all(records)
    await db_session.flush()

    paginator = PageNumberPagination()
    params = PageNumberParams(page=1, size=20, include_count=include_count)
    
    result = await paginator.paginate(db_session, select(PaginationTestModel), params, PaginationTestModel)
    
    assert len(result.data) == 20
    assert result.meta["total"] == expected_total
    assert result.meta["total_pages"] == expected_pages
    assert result.meta["has_next"] is True

@pytest.mark.anyio
@pytest.mark.parametrize("order", ["asc", "desc"])
async def test_cursor_pagination_datetime(db_session: Any, order: str) -> None:
    dt1 = datetime.datetime(2026, 1, 1, 10, 0, 0, 123456)
    dt2 = datetime.datetime(2026, 1, 1, 10, 0, 0, 123456)
    dt3 = datetime.datetime(2026, 1, 1, 10, 0, 0, 654321)

    records = [
        PaginationTestModel(id=1, name="Item 1", created_at=dt1),
        PaginationTestModel(id=2, name="Item 2", created_at=dt2),
        PaginationTestModel(id=3, name="Item 3", created_at=dt3),
    ]
    db_session.add_all(records)
    await db_session.flush()

    paginator = CursorPagination(cursor_field="created_at", order=order)
    
    params1 = CursorParams(size=1)
    page1 = await paginator.paginate(db_session, select(PaginationTestModel), params1, PaginationTestModel)
    assert len(page1.data) == 1
    assert page1.meta["has_more"] is True
    assert page1.meta["next_cursor"] is not None

    expected_first_id = 3 if order == "desc" else 1
    assert page1.data[0].id == expected_first_id

    params2 = CursorParams(size=2, cursor=page1.meta["next_cursor"])
    page2 = await paginator.paginate(db_session, select(PaginationTestModel), params2, PaginationTestModel)
    assert len(page2.data) == 2
    assert page2.meta["has_more"] is False
    
    expected_remaining_ids = [2, 1] if order == "desc" else [2, 3]
    assert [item.id for item in page2.data] == expected_remaining_ids

@pytest.mark.parametrize(
    "corrupted_cursor",
    [
        "invalid_base64_string",
        "eyJhIjogMX0",
        "!!!",
    ]
)
@pytest.mark.anyio
async def test_malformed_cursor_error(db_session: Any, corrupted_cursor: str) -> None:
    paginator = CursorPagination(cursor_field="id")
    params = CursorParams(size=10, cursor=corrupted_cursor)
    
    with pytest.raises(ValidationError) as exc_info:
        await paginator.paginate(db_session, select(PaginationTestModel), params, PaginationTestModel)
        
    assert "Malformed cursor parameter provided." in str(exc_info.value)