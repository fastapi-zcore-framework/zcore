# Multi-Repository Transactions

Ensure data integrity across multiple domain services with atomic Unit of Work orchestration and post-commit event dispatching.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>Transaction Orchestrator</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Status</span><br>
    <strong>Highly Recommended</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Underlying Tech</span><br>
    <strong>SQLAlchemy 2.0 / Unit of Work</strong>
  </div>
</div>

## The Challenge
When business logic spans multiple domains (e.g., creating an **Order**, updating **Inventory**, and deducting **User Balance**), atomicity is critical. If the database update for the balance fails, the order and inventory must not persist. 

In raw FastAPI/SQLAlchemy code, developers often struggle with:
1.  **Premature Commits:** A sub-service calls `db.commit()` inside its own method, finalizing part of the transaction before the rest is ready.
2.  **Ghost Events:** A domain event (like an "Order Confirmation Email") is sent to a message broker, but the database transaction subsequently fails and rolls back. The user receives an email for an order that doesn't exist.
3.  **Session Pollution:** Passing a single session through five different function signatures, making the code brittle and hard to test.

## The ZCore Elegance
ZCore utilizes the **Unit of Work (UOW)** pattern combined with a metadata-aware session [uow.py]. When you wrap operations in a `UnitOfWork` context, it marks the session as `uow_managed`. ZCore's `BaseService` detects this flag and automatically skips its internal commits, delegating the final authority to the UOW. Furthermore, events registered during the transaction are buffered and only dispatched if the commit succeeds.

=== "ZCore Unit of Work"
        :::python
        from zcore import UnitOfWork, Inject
        from zcore.kernel.events import EventDispatcher

        async def checkout_service(
            order_data: OrderCreate,
            order_service: OrderService = Inject(OrderService),
            inventory_service: InventoryService = Inject(InventoryService),
            session: AsyncSession = SessionDep,
            dispatcher: EventDispatcher = Inject(EventDispatcher)
        ):
            # Atomic Boundary
            async with UnitOfWork(session, dispatcher) as uow:
                # Sub-services detect UOW and skip internal commits
                order = await order_service.create(order_data)
                await inventory_service.reduce_stock(order.items)
                
                # Queue event for post-commit dispatch
                uow.register_event("order.placed", {"id": order.id})
                
                # Commit happens automatically at the end of 'async with'

=== "FastAPI Manual Transaction"
        :::python
        @app.post("/checkout")
        async def checkout(data: OrderCreate, db: AsyncSession = Depends(get_db)):
            try:
                # 1. Manual order logic
                order = await create_order(db, data)
                # 2. Manual inventory logic 
                await reduce_stock(db, order.items)
                
                # 3. Manual commit
                await db.commit()
                
                # 4. Manual event trigger
                # If this fails, the user is confused, but the DB is committed.
                await dispatcher.dispatch("order.placed", {"id": order.id})
            except Exception:
                await db.rollback()
                raise

---

## Boundaries & Integration
ZCore provides a structured wrapper around SQLAlchemy's native transaction lifecycle.

*   **Session Native:** `UnitOfWork` operates on a standard `AsyncSession`. You can still call `session.execute()` directly inside a UOW block.
*   **Event Decoupling:** The `EventDispatcher` is a core ZCore component. The UOW strictly manages the *timing* of the dispatch, not the handler logic itself.
*   **Freedom to Bypass:** If you do not use the `UnitOfWork` context, `BaseService` defaults to its `_safe_commit` behavior, which commits the transaction immediately after the service operation concludes.

---

## Under-the-Hood Spec

### 1. The `uow_managed` Flag
Inside `UnitOfWork.__aenter__`, the framework sets `self.session.info["uow_managed"] = True` [uow.py]. The `BaseService._safe_commit` method checks this specific key in the session's internal dictionary [service/base.py]. If present, it treats the session as "borrowed" and skips the `commit()` call, ensuring that only the top-level orchestrator decides when to finalize the data.

### 2. Transactional Event Buffering
The `UnitOfWork` maintains an internal `_pending_events` list [uow.py]. When `uow.register_event()` is called, the event is simply stored in memory. The dispatcher is only invoked in the `commit()` method *after* `await self.session.commit()` has successfully returned. If the database commit raises an exception, the event list is cleared during `rollback()`, preventing "ghost notifications."

### 3. Automatic Exception Handling
The `__aexit__` method of the `UnitOfWork` is designed for safety [uow.py]. If an exception is raised within the `async with` block, it automatically triggers `await self.rollback()`. If the block completes successfully, it triggers `await self.commit()`. This eliminates the need for manual `try/except/rollback` blocks in your business orchestrators.

!!! info "Concurrency Note"
    Events dispatched by the Unit of Work use the `EventDispatcher.dispatch` method, which executes all registered asynchronous handlers concurrently using `asyncio.gather`. This ensures that post-transaction side effects do not serialize your application's response time.