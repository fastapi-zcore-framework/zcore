# Business Service Orchestration

Coordinate domain logic with transactional safety and granular lifecycle hooks.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>Domain Logic Layer</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Status</span><br>
    <strong>Highly Recommended</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Underlying Tech</span><br>
    <strong>Python / Unit of Work</strong>
  </div>
</div>

## The Challenge
When business logic is scattered across routers, applications become fragile and hard to test. Developers struggle with:
- **Transaction Splitting:** Sub-operations accidentally committing early, leaving the database in a partial state if a subsequent step fails.
- **Hook Spaghetti:** Manually triggering side effects (like sending an email or clearing a cache) inside every route handler.
- **Redundant Error Checks:** Repeating `if not item: raise HTTPException(404)` in every single endpoint.
- **Tight Coupling:** Business rules depending directly on HTTP request objects, making them impossible to run in background tasks or CLI scripts.

## The ZCore Elegance
The `BaseService` acts as a pure business orchestrator. It wraps repository calls in a strict **Lifecycle Hook** pipeline and implements the **Safe Commit** protocol. This ensures that domain events are triggered correctly and transactions are only finalized if they are not part of a larger, external `UnitOfWork`.

=== "ZCore Service Orchestration"
        :::python
        from zcore import BaseService, Inject
        from .repositories import OrderRepository
        from .models import Order

        class OrderService(BaseService[Order, OrderCreate, OrderUpdate]):
            def __init__(self, repo: OrderRepository = Inject(OrderRepository)):
                super().__init__(model=Order, repository=repo)

            async def post_create(self, model: Order):
                # Side effect triggered automatically and safely
                await notify_service.send_order_confirmation(model)

            async def pre_update(self, id, schema, partial):
                # Domain validation before DB hit
                if schema.status == "cancelled" and not user.is_admin:
                    raise ForbiddenError("Only admins can cancel orders")

=== "FastAPI Manual Orchestration"
        :::python
        # Logic mixed with HTTP concerns in the router
        @router.post("/")
        async def create_order(data: OrderCreate, db: AsyncSession = Depends(get_db)):
            # 1. Manual Validation
            if data.amount <= 0: raise HTTPException(400)
            
            # 2. Manual DB Logic
            order = Order(**data.model_dump())
            db.add(order)
            try:
                await db.commit() # Dangerous: might break outer transactions
            except Exception:
                await db.rollback()
                raise
                
            # 3. Manual Side Effect (prone to being forgotten)
            await notify_service.send_confirmation(order)
            return order

---

## Boundaries & Integration
ZCore Services are framework-agnostic units that coordinate between the Web and Data layers.

- **Web Independent:** Services never accept `Request` objects or return `JSONResponse`. They operate strictly on Pydantic schemas and SQLAlchemy models, allowing them to be called from Routers, Background Tasks, or CLI commands.
- **Service-to-Service DI:** Use `Inject()` in the constructor to pull in other domain services. ZCore's DI container handles the resolution and ensures correct lifecycles.
- **Hook Bypass:** If you need to perform an operation without triggering hooks (e.g., for data migrations), you can call the "raw" methods like `on_create` or `on_update` directly.
- **Transactional Unity:** Services automatically detect if they are running inside a `UnitOfWork` block and will defer commits to the outer orchestrator.

---

## Under-the-Hood Spec

### 1. The Safe Commit Protocol
Every mutation method in `WriteServiceMixin` concludes with `await self._safe_commit()` [service/base.py]. This method inspects the database session's internal `info` dictionary for the `uow_managed` flag. If a `UnitOfWork` context is active, the service **refrains from committing**, preserving the atomicity of the larger transaction.

### 2. Execution Hook Pipeline
ZCore enforces a strict sequence for all write operations. For example, the `create` method follows this path [service/base.py]:
1.  `pre_create(schema)`: Validation or data enrichment.
2.  `on_create(schema)`: The actual repository write (Flush).
3.  `post_create(model)`: Side effects like logging or events.
4.  `_safe_commit()`: Final transactional boundary check.

### 3. Automated Error Mapping
The `ReadServiceMixin` intercepts empty repository results and automatically raises an `EntityNotFound` exception [service/base.py]. This ensures that your API consistently returns a standardized 404 response through the global exception handler without requiring manual checks in your business code.

### 4. Post-Read Interceptors
Read operations (`get`, `get_list`) include `post_get` and `post_get_multi` hooks [service/base.py]. These are ideal for calculating dynamic properties or performing permission-based masking on model attributes before they reach the web serialization layer.

!!! info "Post-Search Hook"
    The `SearchServiceMixin` also includes a `post_search` hook, allowing you to batch-process results from complex dynamic queries before returning them to the client.