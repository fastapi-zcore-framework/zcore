from __future__ import annotations
import uuid

from datetime import datetime, date

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
    size: int = Field(default=20, le=100)
    page: int = 1
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

    def _is_path_restricted(self, path: str, restricted_set: set[str]) -> bool:
        if not restricted_set:
            return False
        
        normalized_path = path.replace("resource.", "")
        for restricted in restricted_set:
            normalized_restricted = restricted.replace("resource.", "")
            
            if normalized_path == normalized_restricted:
                return True
            if normalized_restricted.startswith(normalized_path + "."):
                return True
            if normalized_path.startswith(normalized_restricted + "."):
                return True
                
        return False
 
    def _validate_request(self, search_in: SearchRequest, max_depth: int = 3) -> None:
        restricted = get_restricted_fields() or set()
        valid_columns = {col.key for col in self.mapper.columns}
        
        if search_in.include:
            for path in search_in.include:
                if self._is_path_restricted(path, restricted):
                    raise ForbiddenError(message=f"Access to relation path '{path}' is restricted due to security policies.")
                
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

    def _validate_filter_field(self, field_path: str, restricted: set[str]) -> None:
        parts = field_path.split(".")
        current_model = self.model
        
        for i, part in enumerate(parts):
            if self._is_restricted(part, restricted):
                raise ForbiddenError(message=f"Filtering by restricted field or relation '{part}' is forbidden.")
            
            if i == len(parts) - 1:
                # Last part must be a valid column on the current model
                valid_columns = {col.key for col in inspect(current_model).columns}
                if part not in valid_columns:
                    raise ValidationError(message=f"Invalid filter field: '{part}' on {current_model.__name__}")
            else:
                # Intermediate parts must be valid relationships
                rel = inspect(current_model).relationships.get(part)
                if not rel:
                    raise ValidationError(message=f"Invalid filter relation: '{part}' on {current_model.__name__}")
                current_model = rel.mapper.class_

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
                    self._validate_filter_field(f.field, restricted)

    @staticmethod
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

        if not f.field:
            return None

        return self._build_expression_for_field(self.model, f.field, f.op, f.value)

    def _build_expression_for_field(self, current_model: Any, field_path: str, op: str, value: Any) -> Any:
        parts = field_path.split(".")
        current_mapper = inspect(current_model)

        if len(parts) == 1:
            col = getattr(current_model, parts[0], None)
            if col is None:
                return None
            return self._compare_column(col, op, value)

        # It's a relationship
        rel_name = parts[0]
        rel = current_mapper.relationships.get(rel_name)
        if not rel:
            return None

        target_model = rel.mapper.class_
        remaining_path = ".".join(parts[1:])

        sub_expr = self._build_expression_for_field(target_model, remaining_path, op, value)
        if sub_expr is None:
            return None

        rel_attr = getattr(current_model, rel_name)
        if rel.uselist:
            return rel_attr.any(sub_expr)
        else:
            return rel_attr.has(sub_expr)

    def _coerce_value(self, col: Any, value: Any) -> Any:
        if value is None:
            return value
            
        if isinstance(value, (list, tuple)):
            return [self._coerce_value(col, v) for v in value]

        try:
            python_type = col.type.python_type
            
            if python_type is date and isinstance(value, str):
                return date.fromisoformat(value.split("T")[0])
                
            if python_type is datetime and isinstance(value, str):
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
                
            if python_type is uuid.UUID and isinstance(value, str):
                return uuid.UUID(value)
                
            if python_type is bool and isinstance(value, str):
                return value.lower() in ("true", "1", "yes", "t", "y")
                
        except (NotImplementedError, AttributeError, ValueError, TypeError):
            pass

        return value
    
    def _compare_column(self, col: Any, op: str, value: Any) -> Any:
        if op == "is_null": return col.is_(None) if value else col.isnot(None)

        if op == "ilike": 
            escaped_value = self._escape_like_wildcards(value)
            return col.ilike(f"%{escaped_value}%", escape="\\")
            
        coerced_value = self._coerce_value(col, value)

        if op == "eq": return col == coerced_value
        if op == "ne": return col != coerced_value
        if op == "gt": return col > coerced_value
        if op == "lt": return col < coerced_value
        if op == "ge": return col >= coerced_value
        if op == "le": return col <= coerced_value
        
        if op == "in": return col.in_(coerced_value if isinstance(coerced_value, (list, tuple)) else [coerced_value])
        
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
        self._validate_request(search_in)
        
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
        offset = (search_in.page - 1) * search_in.size
        return query.offset(offset).limit(search_in.size)