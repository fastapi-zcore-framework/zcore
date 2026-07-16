# Asynchronous Event Orchestration

Loosely coupled communication with concurrent, non-blocking execution and automated failure isolation.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>Infrastructure Engine</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Status</span><br>
    <strong>Core Core</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Underlying Tech</span><br>
    <strong>asyncio / inspect</strong>
  </div>
</div>

## The Challenge
In complex applications, triggering side effects often leads to **Tightly Coupled Spaghetti**. If a `UserService` needs to send a welcome email, notify a Slack channel, and initialize a loyalty account, it must import and call all those services directly. This results in:
1.  **Testing Fragility:** To test a user registration, you must mock the email, slack, and loyalty services.
2.  **Performance Bottlenecks:** Executing side effects sequentially increases the response time of the primary request.
3.  **Failure Propagation:** If the email server is down and raises an exception, the entire user registration fails, even if the database write was successful.

## The ZCore Elegance
The `EventDispatcher` enables a "Fire and Forget" architecture. Services simply dispatch an event, and the dispatcher handles the execution of all subscribers concurrently. Crucially, it isolates failures—an error in one listener will not stop other listeners or the main execution flow.

=== "ZCore Event Dispatching"
        :::python
        from zcore import Inject, EventDispatcher

        class UserService:
            def __init__(self, dispatcher: EventDispatcher = Inject(EventDispatcher)):
                self.dispatcher = dispatcher

            async def register_user(self, schema):
                # ... business logic ...
                user = await self.repo.create(schema)
                
                # Dispatch and let the dispatcher handle the rest
                await self.dispatcher.dispatch("user.registered", user=user)
                return user

        # Subscribers are isolated in their own modules
        @dispatcher.subscribe("user.registered")
        async def send_welcome_email(user):
            await email_service.send(user.email, "Welcome!")

=== "FastAPI Manual Coupling"
        :::python
        # Logic is tightly bound and executed sequentially
        class UserService:
            async def register_user(self, schema):
                user = await self.repo.create(schema)
                
                # 1. Sequential execution (Slow)
                # 2. Tight coupling (Hard to test)
                # 3. Direct failure risk (If email fails, registration fails)
                try:
                    await self.email_service.send(user.email, "Welcome!")
                    await self.slack_service.notify(f"New user: {user.id}")
                except Exception as e:
                    # Manual error handling required for every side effect
                    logger.error(e)
                
                return user

---

## Dispatcher Workflow
The `EventDispatcher` orchestrates a hybrid execution path for both synchronous and asynchronous listeners.

<p align="center">
  <img src="https://raw.githubusercontent.com/fastapi-zcore-framework/zcore/master/docs/assets/events.png" 
  alt="Dispatcher Workflow" width="700">
</p>

---

## Boundaries & Integration
The Event System is an optional orchestration bus that works alongside standard Python calls.

*   **Singleton Registration:** The `Kernel` automatically registers the `EventDispatcher` as a singleton in the DI container. Any component can access it via `Inject(EventDispatcher)` [kernel/engine.py].
*   **Safe for Sync/Async:** You can subscribe with both standard `def` functions and `async def` coroutines. The dispatcher uses `inspect.iscoroutinefunction` to decide how to execute them [kernel/events.py].
*   **Bypass:** If you require a strict, sequential execution where the primary operation *must* fail if a side effect fails, do not use the dispatcher. Instead, call the service methods directly or use a `UnitOfWork` for transactional integrity.

---

## Under-the-Hood Spec

### 1. Concurrent Execution Gather
When `dispatch()` is called, ZCore gathers all asynchronous subscribers and executes them concurrently using `asyncio.gather` [kernel/events.py]. This ensures that multiple side effects (like sending an email and hitting a webhook) do not increase the total response time of the request.

### 2. Failure Isolation (`return_exceptions=True`)
The dispatcher is designed for stability. By using `return_exceptions=True` inside the gather call, ZCore ensures that if one handler raises an exception, the other handlers continue to run [kernel/events.py]. Exceptions are captured, logged via `structlog`, and the dispatcher returns `None` for the failed task instead of crashing the process.

### 3. Dynamic Handler Inspection
The dispatcher uses the `inspect` module to verify handlers during the dispatch phase [kernel/events.py]. It wraps the execution in a `try/except` block even during the "preparation" phase, catching errors that might occur if a handler is improperly configured or has an invalid signature.

!!! info "Transactional Events"
    For database-related events, use the `UnitOfWork`. It buffers events and only calls `dispatcher.dispatch` **after** the database transaction has successfully committed [db/uow.py].