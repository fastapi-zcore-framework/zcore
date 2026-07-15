# Business Services & Lifecycle

Orchestrate domain logic with transactional safety and granular execution hooks.

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
When business logic lives in the router (the "Fat Controller" anti-pattern), applications become impossible to maintain. Developers struggle with:
1.  **Leaky Abstractions:** HTTP logic (headers, status codes) mixing with business rules (tax calculations, validation).
2.  **Transaction Fragility:** Manually managing `commit()` and `rollback()` in every function. If one operation fails halfway, the database is left in an inconsistent state.
3.  **Hook Spaghetti:** Difficulty triggering side effects (like sending an email or clearing a cache) consistently after a database write.
4.  **Redundant Validation:** Re-writing existence checks and ownership validation for every endpoint.

## The ZCore Elegance
The `BaseService` acts as a pure-Python orchestration layer. It wraps repository calls with a rich set of **Lifecycle Hooks** (`pre_create`, `post_update`, etc.) and a smart **Safe Commit** mechanism. This ensures that business rules are executed in the correct order and that transactions are only finalized when all steps succeed.

=== "ZCore Orchestrated Service"
        :::python
        from zcore import BaseService, Inject
        from .repositories import OrderRepository
        from .models import Order

        class OrderService(BaseService[Order, OrderCreate, OrderUpdate]):
            def __init__(self, repository: OrderRepository = Inject(OrderRepository)):
                super().__init__(model=Order, repository=repository)

            async def pre_create(self, schema: OrderCreate):
                # 1. Validation logic before DB hit
                if schema.amount <= 0:
                    raise ValidationError("Invalid amount")

            async def post_create(self, model: Order):
                # 2. Trigger side effects after successful write
                await email_service.send_receipt(model.user_id)

=== "FastAPI Manual Logic"
        :::python
        # Logic scattered in the route handler
        @app.post("/orders")
        async def create_order(data: OrderCreate, db: AsyncSession = Depends(get_db)):
            # 1. Manual Validation
            if data.amount <= 0:
                raise HTTPException(400, "Invalid amount")
            
            # 2. Manual DB Logic
            new_order = Order(**data.model_dump())
            db.add(new_order)
            try:
                await db.commit()
            except Exception:
                await db.rollback()
                raise
                
            # 3. Manual Side Effect
            await email_service.send_receipt(new_order.user_id)
            return new_order

---

## Lifecycle Execution Flow
ZCore services follow a strict execution sequence for every mutation. If any step (including a hook) raises an exception, the entire operation is aborted.

<p align="center">
  <img src="https://raw.githubusercontent.com/fastapi-zcore-framework/zcore/master/docs/assets/4-service.png" 
  alt="Lifecycle Execution Flow" width="700">
</p>

---

## Boundaries & Integration
ZCore services are designed to be framework-agnostic business units.

*   **HTTP Independence:** Services do not accept `Request` objects or return `JSONResponse`. They deal strictly with Pydantic schemas and SQLAlchemy models, making them easily testable in CLI scripts or background workers.
*   **Dependency Injection:** Use the `Inject()` helper to pull in other services (e.g., `NotificationService`) or repositories directly into the constructor.
*   **Bypass:** If you don't need the lifecycle hooks, you can call the core execution methods (e.g., `on_create`, `on_update`) directly, or bypass the service layer entirely by injecting the repository into your router.

---

## Under-the-Hood Spec

### 1. The Safe Commit Protocol
The most critical feature of `WriteServiceMixin` is `_safe_commit()` [service/base.py]. Before committing, the service inspects the database session's internal metadata (`session.info`). If the key `uow_managed` is set to `True`, the service **refrains from committing**. This allows an outer `UnitOfWork` to group multiple service calls into a single atomic transaction without the services "breaking" the transaction boundary prematurely.

### 2. Post-Read Interceptors
Read operations (`get`, `get_list`) include `post_get` and `post_get_multi` hooks [service/base.py]. These are ideal for dynamic property calculation or permission-based filtering that happens after the data leaves the repository but before it reaches the router.

### 3. Automated Error Mapping
The service layer automatically translates missing database records into standardized `EntityNotFound` exceptions [service/base.py]. This ensures that your API consistently returns a `404 Not Found` with a structured error message without you having to write manual `if not result` checks in every method.

### 4. Partial Patch Support
The `update` method intelligently handles the `partial` flag [service/base.py]. When `partial=True`, it instructs the repository to ignore `None` or unset values in the update schema, facilitating clean HTTP `PATCH` implementations.