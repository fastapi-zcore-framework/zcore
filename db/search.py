from __future__ import annotations

from typing import Any, List, Optional, Literal, Type, TypeVar, Dict, Callable
from pydantic import BaseModel, Field

from sqlalchemy import select, asc, desc, inspect, or_, and_
from sqlalchemy.orm import joinedload, selectinload

from app.core.db.setup import Base
from app.core.context.context import get_restricted_fields
from app.core.exception.exceptions import ValidationError, ForbiddenError

ModelType = TypeVar("ModelType", bound=Base)

class FilterItem(BaseModel):
    field: Optional[str] = None
    op: Literal["eq", "ne", "gt", "lt", "ge", "le", "ilike", "in", "is_null", "or", "and"]
    value: Optional[Any] = None
    items: Optional[List[FilterItem]] = None

class SortItem(BaseModel):
    field: str
    order: Literal["asc", "desc"] = "asc"

class SearchRequest(BaseModel):
    filters: Optional[List[FilterItem]] = []
    include: Optional[List[str]] = []
    sort: Optional[List[SortItem]] = []
    limit: int = Field(default=100, le=500)
    skip: int = 0
    page: Optional[int] = None
    cursor: Optional[str] = None

class SearchEngine:
    def __init__(self, model: Type[ModelType]):
        self.model = model
        self.mapper = inspect(model)
        self.custom_handlers: Dict[str, Callable[[Any], Any]] = {}

    def register_handler(self, field_name: str, handler: Callable[[Any], Any]):
        self.custom_handlers[field_name] = handler
        return self

    def _is_restricted(self, field_name: str, restricted_set: set[str]) -> bool:
        if not restricted_set:
            return False
        normalized_name = field_name.replace("resource.", "")
        return (
            field_name in restricted_set or 
            f"resource.{field_name}" in restricted_set or 
            normalized_name in restricted_set
        )

    def _validate_request(self, search_in: SearchRequest, max_depth: int = 3) -> None:
        restricted = get_restricted_fields() or set()
        valid_columns = {col.key for col in self.mapper.columns}
        
        if search_in.include:
            for path in search_in.include:
                parts = path.split(".")
                for part in parts:
                    if self._is_restricted(part, restricted):
                        raise ForbiddenError(message=f"Access to relation or field '{part}' is restricted.")
                
                current_model = self.model
                for part in parts:
                    rel = inspect(current_model).relationships.get(part)
                    if not rel:
                        raise ValidationError(message=f"Invalid include relation path: '{path}'")
                    current_model = rel.mapper.class_

        if search_in.sort:
            for s in search_in.sort:
                if s.field not in valid_columns:
                    raise ValidationError(message=f"Invalid sort field: '{s.field}' on {self.model.__name__}")
                if self._is_restricted(s.field, restricted):
                    raise ForbiddenError(message=f"Sorting by restricted field '{s.field}' is forbidden.")

        if search_in.filters:
            self._validate_filters_recursive(search_in.filters, valid_columns, restricted, current_depth=1, max_depth=max_depth)

    def _validate_filters_recursive(
        self, 
        filters: List[FilterItem], 
        valid_columns: set[str], 
        restricted: set[str], 
        current_depth: int, 
        max_depth: int
    ) -> None:
        if current_depth > max_depth:
            raise ValidationError(message="Search query filter structure is too complex.")

        for f in filters:
            if f.op in ["or", "and"]:
                if f.items:
                    self._validate_filters_recursive(f.items, valid_columns, restricted, current_depth + 1, max_depth)
            else:
                if f.field:
                    if f.field not in valid_columns:
                        raise ValidationError(message=f"Invalid filter field: '{f.field}' on {self.model.__name__}")
                    if self._is_restricted(f.field, restricted):
                        raise ForbiddenError(message=f"Filtering by restricted field '{f.field}' is forbidden.")

    def _escape_like_wildcards(val: Any) -> str:
        if not isinstance(val, str):
            return str(val)
        return val.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    
    def _get_operator_expression(self, f: FilterItem):
        if f.op in ["or", "and"] and f.items:
            sub_exprs = [self._get_operator_expression(item) for item in f.items]
            sub_exprs = [e for e in sub_exprs if e is not None]
            return or_(*sub_exprs) if f.op == "or" else and_(*sub_exprs)

        if f.field in self.custom_handlers:
            return self.custom_handlers[f.field](f.value)

        col = getattr(self.model, f.field, None)
        if col is None: return None

        if f.op == "eq": return col == f.value
        if f.op == "ne": return col != f.value
        if f.op == "gt": return col > f.value
        if f.op == "lt": return col < f.value
        if f.op == "ge": return col >= f.value
        if f.op == "le": return col <= f.value

        if f.op == "ilike": 
            escaped_value = self._escape_like_wildcards(f.value)
            return col.ilike(f"%{escaped_value}%", escape="\\")
            
        if f.op == "in": return col.in_(f.value if isinstance(f.value, (list, tuple)) else [f.value])
        if f.op == "is_null": return col.is_(None) if f.value else col.isnot(None)
        return None


    def _apply_includes(self, query, include_paths: List[str]):
        for path in include_paths:
            parts = path.split(".")
            loader = None
            current_model = self.model
            
            for i, part in enumerate(parts):
                rel = inspect(current_model).relationships.get(part)
                if not rel: break
                
                load_method_name = selectinload if rel.uselist else joinedload
                if i == 0:
                    load_func = selectinload if rel.uselist else joinedload
                    loader = load_func(getattr(current_model, part))
                else:
                    loader = getattr(loader, load_method_name)(getattr(current_model, part))
                
                current_model = rel.mapper.class_
            
            if loader:
                query = query.options(loader)
        return query

    def build_base_query(self, search_in: SearchRequest):
        query = select(self.model)
        
        if search_in.include:
            query = self._apply_includes(query, search_in.include)

        if search_in.filters:
            expressions = [self._get_operator_expression(f) for f in search_in.filters]
            expressions = [e for e in expressions if e is not None]
            if expressions:
                query = query.where(and_(*expressions))

        if search_in.sort:
            for s in search_in.sort:
                col = getattr(self.model, s.field, None)
                if col:
                    query = query.order_by(asc(col) if s.order == "asc" else desc(col))

        return query

    def build_query(self, search_in: SearchRequest):
        query = self.build_base_query(search_in)
        return query.offset(search_in.skip).limit(search_in.limit)