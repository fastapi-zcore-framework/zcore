import uuid
import math
import base64
import json

from typing import Any, Sequence, TypeVar, Generic, Optional, Type, Literal
from datetime import datetime
from sqlalchemy.sql.sqltypes import DateTime
from pydantic import BaseModel, Field

from sqlalchemy import select, func, and_, or_, inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from zcore.utils.helpers import json_dumps

T = TypeVar("T")

class PaginatedResult(Generic[T]):
    def __init__(self, data: Sequence[T], meta: dict[str, Any]):
        self.data = data
        self.meta = meta

class PageNumberParams(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
    sort_by: Optional[str] = None
    sort_order: Literal["asc", "desc"] = "asc"

class CursorParams(BaseModel):
    cursor: Optional[str] = None
    size: int = Field(default=20, ge=1, le=100)

class BasePagination(Generic[T]):
    params_class: Type[BaseModel]

    async def paginate(
        self,
        session: AsyncSession,
        query: Select,
        params: Any,
        model: Any
    ) -> PaginatedResult[T]:
        raise NotImplementedError

class PageNumberPagination(BasePagination[T]):
    params_class = PageNumberParams

    async def paginate(
        self,
        session: AsyncSession,
        query: Select,
        params: PageNumberParams,
        model: Any
    ) -> PaginatedResult[T]:
        page = params.page
        size = params.size
        offset = (page - 1) * size

        if params.sort_by:
            valid_columns = {col.key for col in inspect(model).columns}
            if params.sort_by in valid_columns:
                col = getattr(model, params.sort_by)
                if params.sort_order == "desc":
                    query = query.order_by(col.desc())
                else:
                    query = query.order_by(col.asc())

        count_query = select(func.count()).select_from(query.subquery())
        count_result = await session.execute(count_query)
        total = count_result.scalar_one()

        paginated_query = query.offset(offset).limit(size)
        items_result = await session.execute(paginated_query)
        items = items_result.scalars().all()

        total_pages = math.ceil(total / size) if size > 0 else 0

        meta = {
            "total": total,
            "page": page,
            "size": size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
        return PaginatedResult(data=items, meta=meta)

class CursorPagination(BasePagination[T]):
    params_class = CursorParams

    def __init__(self, cursor_field: str = "id", order: str = "desc"):
        self.cursor_field = cursor_field
        self.order = order.lower()

    def _encode_cursor(self, last_item: Any) -> str:
        value = getattr(last_item, self.cursor_field, None)
        
        payload = {
            "value": value,
            "id": getattr(last_item, "id", "")
        }
        
        json_str = json_dumps(payload)
        return base64.urlsafe_b64encode(json_str.encode()).decode()

    def _decode_cursor(self, cursor_str: str) -> dict[str, Any] | None:
        if not cursor_str:
            return None
        try:
            decoded = base64.urlsafe_b64decode(cursor_str.encode()).decode()
            return json.loads(decoded)
        except Exception:
            return None

    async def paginate(
        self,
        session: AsyncSession,
        query: Select,
        params: CursorParams,
        model: Any
    ) -> PaginatedResult[T]:
        size = params.size
        cursor_data = self._decode_cursor(params.cursor) if params.cursor else None

        col = getattr(model, self.cursor_field)
        pk_col = getattr(model, "id")

        if cursor_data:
            val = cursor_data["value"]
            last_id = cursor_data["id"]
            
            if isinstance(last_id, str):
                try:
                    last_id = uuid.UUID(last_id)
                except ValueError:
                    pass

            if isinstance(col.type, DateTime) and isinstance(val, str):
                try:
                    val = datetime.fromisoformat(val)
                except ValueError:
                    pass

            if self.order == "desc":
                query = query.where(
                    or_(
                        col < val,
                        and_(col == val, pk_col < last_id)
                    )
                )
            else:
                query = query.where(
                    or_(
                        col > val,
                        and_(col == val, pk_col > last_id)
                    )
                )

        if self.order == "desc":
            query = query.order_by(col.desc(), pk_col.desc())
        else:
            query = query.order_by(col.asc(), pk_col.asc())

        paginated_query = query.limit(size + 1)
        items_result = await session.execute(paginated_query)
        items = list(items_result.scalars().all())

        has_more = len(items) > size
        next_cursor = None

        if has_more:
            items = items[:size]
            next_cursor = self._encode_cursor(items[-1])

        meta = {
            "next_cursor": next_cursor,
            "has_more": has_more,
            "size": size
        }
        return PaginatedResult(data=items, meta=meta)