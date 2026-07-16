# Database Event Bridge

Decouple data persistence from application side-effects with secure, isolated event propagation.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>Middleware Bridge</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Status</span><br>
    <strong>Core Utility</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Underlying Tech</span><br>
    <strong>asyncio / structlog</strong>
  </div>
</div>

## The Challenge
Executing side-effects (like invalidating a cache or notifying a external service) directly after a database operation often leads to **Operational Fragility**. In standard implementations:
1.  **Blocked Transactions:** If an event listener is slow or synchronous, it blocks the database session from closing, increasing connection wait times.
2.  **Failure Leakage:** An exception in a "secondary" task (like a failing logging service) can propagate upwards and crash the primary request, even though the database write was successful.
3.  **Tight Coupling:** The database layer becomes aware of high-level application concerns, making the architecture difficult to test or split into microservices later.

## The ZCore Elegance
ZCore provides a **Global Event Bridge** specifically for database lifecycles. By using `dispatch_db_event`, you ensure that database events are transmitted to the application dispatcher within a secure `try/except` wrapper. This guarantees that no matter how many listeners fail or crash, the core database logic remains untouched and the primary execution flow continues.

=== "ZCore Secure Dispatch"
        :::python
        from zcore.db import dispatch_db_event

        async def after_record_created(record):
            # Dispatched via secure bridge
            # Handler failures are logged but isolated
            await dispatch_db_event(
                "db.record_created", 
                payload={"id": record.id}
            )

=== "Manual Unprotected Dispatch"
        :::python
        # Risks crashing the DB operation if a listener fails
        async def after_record_created(record):
            try:
                await dispatcher.dispatch("db.record_created", record.id)
            except Exception as e:
                # You must manually remember to wrap every 
                # dispatch call to prevent leakage
                logger.error(f"Listener failed: {e}")

---

## Event Propagation Flow
The DB Event Bridge acts as a non-blocking safety buffer between the low-level data layer and the high-level event subscribers.

<p align="center">
  <img src="https://raw.githubusercontent.com/fastapi-zcore-framework/zcore/master/docs/assets/db-events.png" 
  alt="Event Propagation Flow" width="700">
</p>

---

## Boundaries & Integration
The DB Event system bridges the gap between infrastructure and domain logic without forcing a lock-in.

*   **Kernel Integration:** During the `main.py` bootstrap, calling `register_db_event_dispatcher(kernel.dispatcher)` links the bridge to the primary application bus [db/events.py].
*   **Decoupled Payloads:** The `payload` argument accepts any Python object or dictionary, allowing you to pass raw database IDs or fully hydrated Pydantic models to your listeners.
*   **Bypass:** If you require a "Strict Dispatch" (where the primary operation *should* fail if a listener fails), you can bypass the bridge and call `kernel.dispatcher.dispatch()` directly.

---

## Under-the-Hood Spec

### 1. The Global Dispatcher Registry
ZCore maintains a private `_global_dispatcher` reference [db/events.py]. This reference is populated once during application startup via `register_db_event_dispatcher`. This "Static Registry" pattern ensures that the database layer can access the event bus without requiring complex Dependency Injection (DI) passing through every repository.

### 2. Async Failure Isolation
The `dispatch_db_event` function is an asynchronous wrapper [db/events.py]. It wraps the underlying dispatcher call in a comprehensive `try/except Exception` block. This is critical because it prevents "Greenlet Leakage" where an unhandled exception in an async event handler could otherwise terminate the entire coroutine stack.

### 3. Structured Diagnostics
When a listener fails, the bridge uses `structlog` to output a detailed error record [db/events.py]. It captures the `event_name` and the specific `payload` that caused the failure, while setting `exc_info=True`. This allows architects to debug failing side-effects from logs without the users ever seeing an error response.

!!! info "Event Handlers"
    Database events are typically used for "Finalized" actions. If you need to trigger logic *within* a transaction, consider using `UnitOfWork.register_event` instead, which delays the bridge dispatch until the commit is confirmed.