from __future__ import annotations

from typing import Any, List, Optional, Literal, Type, TypeVar, Dict, Callable
from pydantic import BaseModel, Field
from sqlalchemy import select, asc, desc, inspect, or_, and_
from sqlalchemy.orm import joinedload, selectinload

from app.core.db.setup import Base

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

class SearchEngine:
    def __init__(self, model: Type[ModelType]):
        self.model = model
        self.mapper = inspect(model)
        self.custom_handlers: Dict[str, Callable[[Any], Any]] = {}

    def register_handler(self, field_name: str, handler: Callable[[Any], Any]):
        self.custom_handlers[field_name] = handler
        return self

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
        if f.op == "ilike": return col.ilike(f"%{f.value}%")
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
                
                load_method = selectinload if rel.uselist else joinedload
                if i == 0:
                    loader = load_method(getattr(current_model, part))
                else:
                    loader = loader.options(load_method(getattr(current_model, part)))
                
                current_model = rel.mapper.class_
            
            if loader:
                query = query.options(loader)
        return query

    def build_query(self, search_in: SearchRequest):
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

        return query.offset(search_in.skip).limit(search_in.limit)