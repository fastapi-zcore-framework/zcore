# Repository Pattern

Decouple business logic from database execution with high-performance, type-safe, and reusable data interfaces.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>Data Access Layer</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Status</span><br>
    <strong>Recommended</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Underlying Tech</span><br>
    <strong>SQLAlchemy 2.0 / Pydantic V2</strong>
  </div>
</div>

## The Challenge
In many FastAPI projects, database queries are scattered directly inside route handlers. This leads to:
- **Repetitive Query Logic:** Manually writing `session.execute(select(...))` and `.scalars().all()` for every endpoint.
- **Leaky Abstractions:** Changing a column name in the database forces you to find and update logic in dozens of router files.
- **Testing Hardship:** Mocking a raw `AsyncSession` with complex chain calls is significantly harder than mocking a high-level `get_by_id` method.
- **Inconsistent Pagination:** Different developers implementing offset or cursor logic differently, leading to unpredictable API behavior.

## The ZCore Elegance
The `BaseRepository` provides a robust, pre-optimized set of CRUD and search operations. It leverages Python generics to ensure type safety across your domain and integrates seamlessly with ZCore’s specialized search and pagination engines. By inheriting from the repository, you gain standardized methods for batch operations, partial updates, and optimized existence checks out of the box.

=== "ZCore Repository"
        :::python
        from zcore import BaseRepository
        from .models import User
        from .schemas import UserCreate, UserUpdate

        class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
            def __init__(self, db: AsyncSession):
                super().__init__(model=User, db=db)
                
            # Custom logic remains clean and isolated
            async def get_active_users(self):
                query = self._get_base_query().where(User.is_active == True)
                result = await self.db.execute(query)
                return result.scalars().all()
        
=== "Manual SQLAlchemy Implementation"
        :::python
        # Repetitive boilerplate required for every entity
        async def get_user(db: AsyncSession, user_id: uuid.UUID):
            query = select(User).where(User.id == user_id)
            result = await db.execute(query)
            return result.scalars().first()

        async def update_user(db: AsyncSession, user_id: uuid.UUID, data: UserUpdate):
            query = select(User).where(User.id == user_id)
            user = (await db.execute(query)).scalars().first()
            if user:
                for key, value in data.model_dump().items():
                    setattr(user, key, value)
                await db.flush()
            return user

---

## Boundaries & Integration
ZCore Repositories are designed to be thin wrappers that expose the full power of SQLAlchemy.

- **Standard AsyncSession:** The `self.db` attribute is a standard `AsyncSession`. You can execute any raw SQL or complex SQLAlchemy expression whenever the scaffolded methods are insufficient.
- **Query Extensibility:** Use `_get_base_query()` to define default filters (e.g., Soft Delete logic) and `_extend_query()` for custom joins that should apply to all read operations.
- **Eager Loading:** All read methods (`get`, `get_list`, etc.) accept an `options` parameter for standard SQLAlchemy loader options like `joinedload` or `selectinload`.
- **Selective Loading:** The `fields` parameter allows you to perform `load_only` queries, ensuring you only fetch the data you actually need from the wire.

---

## Under-the-Hood Spec

### 1. Automatic PK Inspection
Upon initialization, `BaseRepository` uses the SQLAlchemy `inspect` module to automatically identify the model's primary key [db/repository.py]. It maps this to `self.pk` and `self.pk_name`, allowing the generic CRUD methods to work regardless of whether your primary key is named `id`, `uuid`, or a custom field.

### 2. The `get_by_ids` Fast Path
The `get_by_ids` implementation includes a high-performance "fast path" [db/repository.py]. If an empty list is passed as the `ids` parameter, the repository returns an empty sequence immediately without making a network round-trip to the database engine.

### 3. Optimized Existence Checks
The `exist()` method is optimized for minimal database overhead [db/repository.py]. Instead of loading a full model instance, it executes a `select(1).where(...)` with a `limit(1)` clause, which is significantly faster and consumes less memory on both the application and database server.

### 4. Flush-Oriented Mutations
All write operations (`create`, `update`, `delete`) in the repository use `await self.db.flush()` and `await self.db.refresh()` instead of `commit()` [db/repository.py]. This ensures that changes are validated by the database but remain part of an open transaction, allowing the `UnitOfWork` to manage the final atomic commit boundary.

!!! info "Cursor Field"
    By default, the repository uses the primary key as the `cursor_field` for keyset pagination. You can override this in your subclass (e.g., `self.cursor_field = "created_at"`) to support stable pagination on chronological data.