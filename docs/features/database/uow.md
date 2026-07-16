# Unit of Work (Atomic Transactions)

Coordinate multiple domain operations into a single atomic transaction with safe, post-commit event dispatching.

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
    <strong>SQLAlchemy 2.0 / asyncio</strong>
  </div>
</div>

## The Challenge
In complex business flows (e.g., a **Checkout** involving Inventory, Payment, and Shipping), maintaining data integrity is difficult. Standard implementations often suffer from:
1.  **Premature Commits:** A sub-service (e.g., `InventoryService`) commits its changes independently. If the subsequent `PaymentService` fails, the inventory is already deducted, leaving the system in an inconsistent state.
2.  **Ghost Notifications:** An event (like a "Welcome Email") is dispatched as soon as a user is created. If the database transaction later fails and rolls back, the user receives an email for an account that doesn't exist.
3.  **Boilerplate Fatigue:** Wrapping every multi-step operation in `try/except/rollback` blocks leads to noisy, error-prone code.

## The ZCore Elegance
The `UnitOfWork` (UOW) acts as the single source of truth for a transaction's lifecycle. It marks the database session as "Managed," signaling to all internal ZCore services that they must defer their commits. Furthermore, it provides an event buffer that guarantees domain events are **only dispatched after** a successful database commit.

=== "ZCore Unit of Work"
        :::python
        from zcore import UnitOfWork, Inject

        async def checkout_flow(
            data: CheckoutSchema,
            order_service: OrderService = Inject(OrderService),
            inventory_service: InventoryService = Inject(InventoryService),
            dispatcher: EventDispatcher = Inject(EventDispatcher),
            session: AsyncSession = SessionDep
        ):
            # 1. Atomic context manager
            async with UnitOfWork(session, dispatcher) as uow:
                # Sub-services detect UOW and skip internal commits
                order = await order_service.place_order(data)
                await inventory_service.reduce_stock(order.items)
                
                # 2. Register event for post-commit dispatch
                uow.register_event("order.placed", {"id": order.id})
                
                # 3. Auto-commit on exit / Auto-rollback on exception

=== "Raw SQLAlchemy Implementation"
        :::python
        async def checkout_flow(data, db, dispatcher):
            try:
                # 1. Manual order logic
                order = await create_order(db, data)
                # 2. Manual inventory logic
                await reduce_stock(db, order.items)
                
                # 3. Manual commit
                await db.commit()
                
                # 4. Manual event dispatch (Risk: if commit failed, 
                # or if this fails, logic becomes messy)
                await dispatcher.dispatch("order.placed", {"id": order.id})
            except Exception:
                # 5. Manual rollback
                await db.rollback()
                raise

---

## Boundaries & Integration
ZCore’s UOW is a high-level orchestrator that respects underlying SQLAlchemy protocols.

*   **Session Native:** The UOW operates on a standard SQLAlchemy `AsyncSession`. You can perform raw SQL executions within a UOW block, and they will be part of the same atomic transaction.
*   **Service Interlock:** ZCore's `BaseService` is programmed to check for the `uow_managed` flag. It will only commit if it is the primary owner of the session, ensuring it doesn't break a UOW's boundary [service/base.py].
*   **Bypass:** For single-operation requests (like a simple GET or a standalone POST), you do not need the UOW. ZCore services will handle their own "Safe Commit" logic automatically.

---

## Under-the-Hood Spec

### 1. The `uow_managed` Metadata
When entering the `async with` block, the UOW sets `session.info["uow_managed"] = True` [db/uow.py]. This is a standard SQLAlchemy metadata dictionary. ZCore services inspect this flag before calling `commit()`. If `True`, they execute a `flush()` to send changes to the DB buffer but skip the `commit()`, delegating finality to the UOW.

### 2. Transactional Event Buffering
The UOW maintains an internal `_pending_events` list [db/uow.py]. When `register_event()` is called, the event is not fired immediately. Instead, it is stored in the buffer. The UOW only iterates through this list and calls `dispatcher.dispatch()` **after** `session.commit()` has successfully returned.

### 3. Automated Lifecycle Safety
The `__aexit__` method handles the logic of the transaction [db/uow.py]. If an exception was raised inside the block, it triggers `rollback()` and clears the event buffer. If no exception occurred, it triggers `commit()`. This ensures that even if a developer forgets to call commit manually, the transaction is handled correctly by the context manager.

!!! success "Event Isolation"
    If a database commit succeeds but an event handler subsequently fails, the database remains committed. ZCore logs the event handler failure separately, ensuring that side effects (like failing to send an email) do not retroactively break your database integrity.