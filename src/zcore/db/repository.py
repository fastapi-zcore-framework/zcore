"""ZCore Database Repository Pattern Layer.

This module provides a Repository pattern implementation for SQLAlchemy 
2.0 and Pydantic V2. It decouples business logic from database interactions by exposing 
highly specialized, reusable interfaces divided into read, write, and search capabilities. 
It supports dynamic pagination, eager load optimization, and field pruning.
"""

from pydantic import BaseModel
from typing import TYPE_CHECKING, Generic, TypeVar, Type, Any, Sequence, Optional, List
from sqlalchemy import select, inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.interfaces import ExecutableOption
from sqlalchemy.orm import load_only

from zcore.db.setup import Base
from zcore.db.pagination import (
    PageNumberPagination, 
    CursorPagination, 
    CursorParams
)

if TYPE_CHECKING:
    from zcore.db.search import SearchRequest, SearchEngine

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class AbstractRepository(Generic[ModelType]):
    """Abstract base repository class defining the fundamental schema interface.

    Any custom repository class implementation in ZCore must inherit from this abstraction or
    its mixins.

    Attributes:
        db: The active asynchronous database session.
        model: The SQLAlchemy model class bound to the repository instance.
        pk: The SQLAlchemy primary key column representation of the bound model.
        pk_name: The string identifier name of the primary key field.
        cursor_field: The field name to utilize during keyset pagination lookups.
    """

    db: AsyncSession
    model: Type[ModelType]
    pk: Any
    pk_name: str
    cursor_field: str

    async def get(
        self, 
        id: Any, 
        fields: Optional[List[Any]] = None, 
        options: Optional[List[ExecutableOption]] = None
    ) -> Optional[ModelType]:
        """Fetch a single record by its primary key identifier.

        Args:
            id: The primary key value of the targeted record.
            fields: Specific entity fields to selectively load. If None, all attributes 
                are loaded. Defaults to None.
            options: Additional SQLAlchemy executable options (e.g., join-loads). 
                Defaults to None.

        Returns:
            The retrieved model instance, or None if no matching record is found.

        Raises:
            NotImplementedError: Raised if the subclass does not implement this method.
        """
        raise NotImplementedError

    async def get_by_ids(
        self, 
        ids: List[Any], 
        fields: Optional[List[Any]] = None, 
        options: Optional[List[ExecutableOption]] = None
    ) -> Sequence[ModelType]:
        """Fetch a sequence of records matching a list of primary keys.

        Args:
            ids: A list of primary key values to look up.
            fields: Specific entity fields to selectively load. If None, all attributes 
                are loaded. Defaults to None.
            options: Additional SQLAlchemy executable options (e.g., join-loads). 
                Defaults to None.

        Returns:
            A sequence of retrieved database model instances.

        Raises:
            NotImplementedError: Raised if the subclass does not implement this method.
        """
        raise NotImplementedError


class ReadRepositoryMixin(AbstractRepository[ModelType]):
    """Mixin implementing core query and retrieval operations for repositories.

    Provides common read capabilities including existence checks, single record fetches,
    multi-key batch retrievals, and paginated listings.
    """

    async def exist(self, id: Any) -> bool:
        """Check if a record with the specified primary key exists in the database.

        Args:
            id: The primary key of the target record.

        Returns:
            True if the record is found, False otherwise.
        """
        query = select(self.model.id).where(self.pk == id).limit(1)
        result = await self.db.execute(query)
        return result.first() is not None

    async def get(
        self, 
        id: Any, 
        fields: Optional[List[Any]] = None, 
        options: Optional[List[ExecutableOption]] = None
    ) -> Optional[ModelType]:
        """Fetch a single record by its primary key.

        Args:
            id: The primary key of the target record.
            fields: Specific entity fields to selectively load. Defaults to None.
            options: Additional SQLAlchemy execution options. Defaults to None.

        Returns:
            The retrieved model instance, or None if not found.
        """
        query = select(self.model).where(self.pk == id)
        if fields:
            query = query.options(load_only(*fields))
        if options:
            query = query.options(*options) if isinstance(options, list) else query.options(options)
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_by_ids(
        self, 
        ids: List[Any], 
        fields: Optional[List[Any]] = None, 
        options: Optional[List[ExecutableOption]] = None
    ) -> Sequence[ModelType]:
        """Fetch a sequence of records matching the provided primary key list.

        This method includes a fast path that returns an empty sequence directly 
        if the requested `ids` parameter is empty, avoiding unnecessary database hits.

        Args:
            ids: A list of target primary key values.
            fields: Specific entity fields to selectively load. Defaults to None.
            options: Additional SQLAlchemy execution options. Defaults to None.

        Returns:
            A sequence of retrieved database model instances.
        """
        # Fast path: Skip DB hit if empty list passed
        if not ids:
            return []
            
        query = select(self.model).where(self.pk.in_(ids))
        if fields:
            query = query.options(load_only(*fields))
        if options:
            query = query.options(*options) if isinstance(options, list) else query.options(options)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_list(
        self, 
        pagination: Any = None, 
        fields: Optional[List[Any]] = None, 
        options: Optional[List[ExecutableOption]] = None
    ) -> Any:
        """Fetch a paginated or complete list of records.

        Args:
            pagination: Pagination parameters. Supports CursorParams or standard page parameters.
                If None, fetches the entire unfiltered result set. Defaults to None.
            fields: Specific entity fields to selectively load. Defaults to None.
            options: Additional SQLAlchemy execution options. Defaults to None.

        Returns:
            A list of matching records, or a paginated response container containing 
            items and metadata.
        """
        query = select(self.model)
        if fields:
            query = query.options(load_only(*fields))
        if options:
            query = query.options(*options) if isinstance(options, list) else query.options(options)
        
        if pagination is None:
            result = await self.db.execute(query)
            return result.scalars().all()
            
        paginator = CursorPagination(self.cursor_field) if isinstance(pagination, CursorParams) else PageNumberPagination()
        return await paginator.paginate(self.db, query, pagination, self.model)


class WriteRepositoryMixin(Generic[ModelType, CreateSchemaType, UpdateSchemaType], AbstractRepository[ModelType]):
    """Mixin implementing data modification and persistence operations.

    Provides database writes, including single and multi-record insertions, dynamic
    updates (with partial patch support), and single or multi-record deletions. Matches operations
    with Unit of Work patterns by utilizing `flush` instead of direct `commit`.
    """

    async def create(self, schema: CreateSchemaType) -> ModelType:
        """Create a new database record from a validated creation schema.

        Args:
            schema: The validated Pydantic model containing properties for the new record.

        Returns:
            The created and refreshed database model instance.
        """
        record = self.model(**schema.model_dump())
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def create_multi(self, schemas: List[CreateSchemaType], refresh: bool = False) -> Sequence[ModelType]:
        """Create multiple database records from a list of validation schemas.

        Args:
            schemas: A list of Pydantic schemas representing the new database objects.
            refresh: If True, executes an explicit database refresh on each record individually.
                Defaults to False.

        Returns:
            A sequence of created database model instances.
        """
        if not schemas:
            return []
            
        records = [self.model(**schema.model_dump()) for schema in schemas]
        self.db.add_all(records)
        await self.db.flush()
        if refresh:
            for record in records:
                await self.db.refresh(record)
        return records

    async def update(self, id: Any, schema: UpdateSchemaType, partial: bool = False) -> Optional[ModelType]:
        """Update an existing database record.

        Args:
            id: The primary key identifier of the record to update.
            schema: The Pydantic update schema containing modified parameters.
            partial: If True, applies modifications as a partial patch (ignoring unset fields).
                If False, updates the record using all fields. Defaults to False.

        Returns:
            The updated and refreshed database model instance, or None if the record was not found.
        """
        record = await self.get(id)
        if not record:
            return None
        update_data = schema.model_dump(exclude_unset=partial)
        for field, value in update_data.items():
            setattr(record, field, value)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def update_multi(
        self, 
        data: dict[Any, UpdateSchemaType], 
        partial: bool = False, 
        refresh: bool = False
    ) -> Sequence[ModelType]:
        """Batch update multiple database records mapped by their primary keys.

        Args:
            data: A dictionary mapping target primary keys to their respective update schemas.
            partial: If True, fields omitted in the schema payload are skipped. Defaults to False.
            refresh: If True, refreshes the instance attributes from the database after flushing.
                Defaults to False.

        Returns:
            A sequence containing the updated database model instances.
        """
        if not data:
            return []
            
        records = await self.get_by_ids(ids=list(data.keys()))
        record_map = {getattr(r, self.pk_name): r for r in records}
        updated_records = []
        for record_id, schema in data.items():
            record = record_map.get(record_id)
            if record:
                update_data = schema.model_dump(exclude_unset=partial)
                for field, value in update_data.items():
                    setattr(record, field, value)
                updated_records.append(record)
        await self.db.flush()
        if refresh:
            for record in updated_records:
                await self.db.refresh(record)
        return updated_records

    async def delete(self, id: Any) -> Optional[ModelType]:
        """Delete a single record by its primary key identifier.

        Args:
            id: The primary key value of the target record to delete.

        Returns:
            The deleted database model instance, or None if the record was not found.
        """
        record = await self.get(id)
        if not record:
            return None
        await self.db.delete(record)
        await self.db.flush()
        return record

    async def delete_multi(self, ids: List[Any]) -> Sequence[ModelType]:
        """Delete multiple records matching the provided list of primary keys.

        Args:
            ids: A list of primary key values of records to delete.

        Returns:
            A sequence containing the deleted database model instances.
        """
        if not ids:
            return []
            
        records = await self.get_by_ids(ids=ids)
        for record in records:
            await self.db.delete(record)
        await self.db.flush()
        return records


class SearchRepositoryMixin(AbstractRepository[ModelType]):
    """Mixin coordinating structured application search operations.

    Integrates with the framework search engine to generate queries with complex 
    filter, sorting, and relation preloading patterns.
    """

    async def search(self, search_in: "SearchRequest", pagination: Any = None) -> Any:
        """Search and filter database models dynamically.

        Utilizes the system `SearchEngine` to parse filters, apply relation joins, 
        and handle sorting rules, yielding either a plain sequence or paginated lists.

        Args:
            search_in: A SearchRequest parameter configuration representing constraints.
            pagination: Pagination settings (CursorParams or standard page parameter mapping).
                Defaults to None.

        Returns:
            A paginated response object containing matches, or a complete list of 
            unpaginated models.
        """
        from zcore.db.search import SearchEngine
        engine = SearchEngine(self.model)
        query = engine.build_base_query(search_in)
        if pagination is None:
            result = await self.db.execute(query)
            return result.scalars().all()
            
        paginator = CursorPagination(self.cursor_field) if isinstance(pagination, CursorParams) else PageNumberPagination()
        return await paginator.paginate(self.db, query, pagination, self.model)


class BaseRepository(
    Generic[ModelType, CreateSchemaType, UpdateSchemaType],
    ReadRepositoryMixin[ModelType],
    WriteRepositoryMixin[ModelType, CreateSchemaType, UpdateSchemaType],
    SearchRepositoryMixin[ModelType]
):
    """The default implementation combining Read, Write, and Search capabilities.

    Integrates standard read, write, and dynamic query routines with default primary key 
    inspection logic.
    """

    def __init__(self, model: Type[ModelType], db: AsyncSession):
        """Initialize the BaseRepository.

        Dynamically inspects the model schema definition to locate and map 
        the primary key column and attributes automatically.

        Args:
            model: The SQLAlchemy declarative model class linked to this repository.
            db: The active asynchronous SQLAlchemy session.
        """
        self.model = model
        self.db = db
        self.pk = inspect(self.model).primary_key[0]
        self.pk_name = self.pk.name
        self.cursor_field = self.pk_name