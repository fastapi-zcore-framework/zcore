import uuid
import math
import base64
from typing import Any, Sequence, TypeVar, Generic, Optional, Type, Literal
from datetime import datetime
from pydantic import BaseModel, Field

from sqlalchemy.sql.sqltypes import DateTime
from sqlalchemy.sql import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, inspect

from zcore.utils.helpers import json_dumps, json_loads
from zcore.exceptions.base import ValidationError

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
    include_count: bool = True

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
            if params.sort_by not in valid_columns:
                raise ValidationError(message=f"Invalid sort field: '{params.sort_by}' on {model.__name__}")
                
            col = getattr(model, params.sort_by)
            if params.sort_order == "desc":
                query = query.order_by(col.desc())
            else:
                query = query.order_by(col.asc())

        total = None
        total_pages = None
        has_next = False
        has_prev = page > 1

        if params.include_count:
            cleaned_query = query.order_by(None)
            count_query = select(func.count()).select_from(cleaned_query.subquery())
            
            count_result = await session.execute(count_query)
            total = count_result.scalar_one()
            total_pages = math.ceil(total / size) if size > 0 else 0
            has_next = page < total_pages
            
            paginated_query = query.offset(offset).limit(size)
            items_result = await session.execute(paginated_query)
            items = list(items_result.scalars().all())
        else:
            paginated_query = query.offset(offset).limit(size + 1)
            items_result = await session.execute(paginated_query)
            items = list(items_result.scalars().all())
            
            if len(items) > size:
                items = items[:size]
                has_next = True

        meta = {
            "total": total,
            "page": page,
            "size": size,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev
        }
        return PaginatedResult(data=items, meta=meta)

class CursorPagination(BasePagination[T]):
    params_class = CursorParams

    def __init__(self, cursor_field: str = "id", order: str = "desc"):
        self.cursor_field = cursor_field
        self.order = order.lower()

    def _encode_cursor(self, last_item: Any) -> str:
        value = getattr(last_item, self.cursor_field, None)
        if isinstance(value, datetime):
            value = value.isoformat()
            
        payload = {
            "value": value,
            "id": str(getattr(last_item, "id", ""))
        }
        
        json_str = json_dumps(payload)
        encoded = base64.urlsafe_b64encode(json_str.encode()).decode()
        return encoded.rstrip("=")

    def _decode_cursor(self, cursor_str: str) -> dict[str, Any] | None:
        if not cursor_str:
            return None
        try:
            padding_needed = (4 - len(cursor_str) % 4) % 4
            cursor_str += "=" * padding_needed
            decoded = base64.urlsafe_b64decode(cursor_str.encode()).decode()
            decoded_dict = json_loads(decoded)
            if not isinstance(decoded_dict, dict) or "value" not in decoded_dict or "id" not in decoded_dict:
                raise ValidationError(message="Malformed cursor parameter provided.")
            return decoded_dict
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(message="Malformed cursor parameter provided.") from e

    async def paginate(
        self,
        session: AsyncSession,
        query: Select,
        params: CursorParams,
        model: Any
    ) -> PaginatedResult[T]:
        size = params.size
        cursor_data = self._decode_cursor(params.cursor) if params.cursor else None

        valid_columns = {col.key for col in inspect(model).columns}
        if self.cursor_field not in valid_columns:
            raise ValidationError(message=f"Invalid cursor field: '{self.cursor_field}' on {model.__name__}")

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