# Repository Pattern & Persistence

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
In many FastAPI projects, database queries are scattered directly inside route handlers. This "Fat Router" anti-pattern leads to:
1.  **Repetitive Boilerplate:** Manually writing `session.execute(select(...))` and `.scalars().all()` for every endpoint.
2.  **Brittle Pagination:** Inconsistent implementations of offset or cursor logic across different domains.
3.  **Testing Hardship:** Difficulty mocking database interactions because the business logic is tightly coupled with SQLAlchemy's execution engine.
4.  **Inefficient Queries:** Forgetting to apply `load_only` or missing eager-loading configurations, leading to over-fetching or N+1 problems.

## The ZCore Elegance
The `BaseRepository` provides a robust, pre-optimized set of CRUD and search operations. It automatically inspects your model to identify primary keys and coordinates with ZCore's pagination and search engines. By inheriting from `BaseRepository`, you gain standardized behaviors for selective field loading, batch operations, and partial updates.

=== "ZCore Repository Interface"
        :::python
        from zcore import BaseRepository
        from .models import Product
        from .schemas import ProductCreate, ProductUpdate

        class ProductRepository(BaseRepository[Product, ProductCreate, ProductUpdate]):
            def __init__(self, db: AsyncSession):
                # No boilerplate required. BaseRepository handles:
                # .get(), .get_list(), .search(), exist(), get_by_ids()
                # .create(), .create_multi(), .update(), .update_multi()
                # .delete(), .delete_multi()
                super().__init__(model=Product, db=db)
                
            async def get_expensive_products(self, threshold: float):
                # Custom logic is clean and isolated
                query = self._get_base_query().where(Product.price > threshold)
                result = await self.db.execute(query)
                return result.scalars().all()

=== "Manual SQLAlchemy Boilerplate"
        :::python
        # For every model, you must manually repeat:
        async def get_product(db: AsyncSession, id: uuid.UUID):
            query = select(Product).where(Product.id == id)
            result = await db.execute(query)
            item = result.scalar_one_or_none()
            if not item: return None
            return item

        async def update_product(db: AsyncSession, id: uuid.UUID, data: dict):
            item = await get_product(db, id)
            for key, value in data.items():
                setattr(item, key, value)
            await db.flush() # Remember to flush but not commit? 
            return item

---

## Boundaries & Integration
ZCore repositories are abstractions that expose, rather than hide, the power of SQLAlchemy.

*   **Direct DB Access:** The `self.db` attribute is a standard SQLAlchemy `AsyncSession`. You can run raw SQL or complex `expression` constructs whenever needed.
*   **Query Customization:** Use `_get_base_query()` to start every query with default filters (e.g., Soft Delete logic) or `_extend_query()` to apply global modifications.
*   **Eager Loading:** All read methods (`get`, `get_list`, `get_by_ids`) accept an `options` parameter where you can pass standard SQLAlchemy loader options like `joinedload` or `selectinload`.
*   **Selective Fields:** The `fields` parameter allows you to pass a list of model attributes to perform a `load_only` query, optimizing network traffic between the app and the database.

---

## Under-the-Hood Spec

### 1. Automatic PK Inspection
Upon initialization, `BaseRepository` utilizes the SQLAlchemy `inspect()` module to automatically locate the model's primary key [repository.py]. It maps this to `self.pk` and `self.pk_name`, allowing generic CRUD methods to function correctly regardless of whether your primary key is named `id`, `uuid`, or `pk`.

### 2. The `get_by_ids` Fast-Path
The `get_by_ids` method includes a silent performance optimization: if an empty list is passed as the `ids` argument, the repository returns an empty sequence immediately without making a network round-trip to the database [repository.py].

### 3. Flush-Oriented Mutations
All mutation methods (`create`, `update`, `delete`) in the repository utilize `await self.db.flush()` instead of `commit()` [repository.py]. This ensures that changes are sent to the database's transaction buffer but remain uncommitted, allowing the `UnitOfWork` or a higher-level service to manage the final atomic transaction boundary.

### 4. Search Engine Integration
The `search()` method is a bridge to the `SearchEngine`. It translates a `SearchRequest` (containing JSON-based filters and sorts) into a validated SQLAlchemy query, ensuring that even dynamic queries respect the security context and depth limits [repository.py, search.py].