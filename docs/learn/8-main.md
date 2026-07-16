# Application Bootstrapping

The unified entry point where infrastructure, security, and domain plugins converge into a running FastAPI instance.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>Entry Point</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Status</span><br>
    <strong>Mandatory Root</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Underlying Tech</span><br>
    <strong>FastAPI / Kernel</strong>
  </div>
</div>

## The Challenge
In many FastAPI projects, the `main.py` file eventually becomes a "God Object"—a massive procedural script that handles logging, database initialization, middleware ordering, exception mapping, and router registration. This leads to:
1.  **Fragile Middleware Ordering:** Placing `Authentication` after `Routing` or `Session` management after `Logging`, causing cryptic errors.
2.  **Infrastructure Leaks:** Database connection strings and logging configurations mixed with business route definitions.
3.  **Hard-to-Test Entry Points:** Because everything is tightly coupled in one file, spinning up the app for integration tests without the entire stack becomes difficult.

## The ZCore Elegance
ZCore provides a declarative bootstrap template. Instead of writing procedural logic, you configure the `Kernel`, register your domain `Plugins`, and attach the core middlewares. The `main.py` serves strictly as an **Orchestrator**, delegating the heavy lifting to the infrastructure managers and domain plugins.

=== "ZCore main.py (Orchestrated)"
        :::python
        # Auto-generated via 'zc init'
        from fastapi import FastAPI
        from zcore import Kernel, settings
        from zcore.web import RequestLogMiddleware, ScopedDependencyMiddleware
        from zcore.exceptions import app_exception_handler, AppException
        from zcore.db import db_manager, register_db_event_dispatcher
        from zcore.logging import setup_logging

        # 1. Infrastructure Setup
        setup_logging()
        db_manager.init_app(db_url=settings.DATABASE_URL)

        # 2. Kernel & Plugin Registration
        kernel = Kernel()
        kernel.add_plugin(UsersPlugin()) # Your domain logic
        register_db_event_dispatcher(kernel.dispatcher)

        # 3. FastAPI Bootstrap
        app = FastAPI(title=settings.PROJECT_NAME, lifespan=kernel.lifespan)
        kernel.setup(app)

        # 4. Middleware & Error Handlers
        app.add_middleware(RequestLogMiddleware)
        app.add_middleware(ScopedDependencyMiddleware)
        app.add_exception_handler(AppException, app_exception_handler)

=== "FastAPI Raw (Procedural)"
        :::python
        # Typical 'main.py' in a standard project
        app = FastAPI()

        @app.on_event("startup")
        async def startup():
            # Manual procedural setup
            logging.config.dictConfig(LOG_CONFIG)
            await database.connect()
            # What if this fails? Is the error caught?
            await cache.connect()

        # Manual Error Handling for every custom exception
        @app.exception_handler(MyCustomError)
        async def handler(request, exc):
            return JSONResponse(...)

        # Middleware ordering is manual and invisible
        app.add_middleware(SessionMiddleware)
        app.add_middleware(AuthMiddleware)

        app.include_router(users_router)
        # File grows to 500+ lines...

---

## Bootstrapping Lifecycle
When you launch your application (via `zc run`), ZCore executes the following phases in a strict, predictable sequence:

<p align="center">
  <img src="https://raw.githubusercontent.com/fastapi-zcore-framework/zcore/master/docs/assets/8-main.png" 
  alt="Bootstrapping Lifecycle" width="700">
</p>

---

## Boundaries & Integration
The ZCore bootstrap process is designed to be a "wrapper" that stays out of your way.

*   **FastAPI Native:** The `app` variable is a standard `FastAPI()` instance. You can use any native FastAPI feature, such as custom lifespan context managers or third-party middlewares, alongside ZCore.
*   **Infrastructure Isolation:** Database and Logging initialization happen before the app starts. This ensures that infrastructure is "warm" before any plugin logic is executed.
*   **Manual Overrides:** If you need to add a router that isn't part of a plugin, you can simply call `app.include_router()` in `main.py` as you normally would.

---

## Under-the-Hood Spec

### 1. Scoped Middleware Dependency
The `ScopedDependencyMiddleware` is critical. It initializes a unique `uuid4` correlation ID for every request and sets up the request-scoped DI container [web/middleware.py]. Most importantly, it injects the active `AsyncSession` into the container, ensuring that all services and repositories within that request share the same database transaction.

### 2. Centralized Exception Mapping
The `app_exception_handler` intercepts any exception inheriting from `AppException` [exceptions/handlers.py]. It automatically logs the error with structured metadata (request path, method, and correlation ID) and wraps the error message in the standardized `ResponseWrapper` JSON envelope, ensuring your API never returns a raw traceback.

### 3. The DB-Event Bridge
By calling `register_db_event_dispatcher(kernel.dispatcher)`, you bridge the database layer with the application event system [db/events.py]. This allows low-level database operations (like a transaction commit) to trigger high-level domain events (like sending a notification) through a loosely coupled, non-blocking bus.

!!! success "Project Ready"
    You have now completed the core ZCore Tutorial. Your project is scaffolded, your infrastructure is secure, and your domain logic is structured. Proceed to the **How-To Guides** to implement advanced features like JWT Auth or Multi-Repository Transactions.