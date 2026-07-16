# Application Entry Point

The centralized orchestrator where infrastructure, security context, and domain plugins converge into a unified FastAPI application.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>Bootstrap Orchestrator</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Status</span><br>
    <strong>Core Requirement</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Underlying Tech</span><br>
    <strong>FastAPI / ASGI / ZCore Kernel</strong>
  </div>
</div>

## The Challenge
In standard FastAPI projects, the `main.py` file frequently evolves into a "God File"—a massive procedural script handling everything from logging and database initialization to middleware ordering and raw router includes. This results in:
- **Procedural Fragility:** Changing the order of a single line (e.g., placing Auth middleware after Routing) causes silent, critical failures.
- **Initialization Race Conditions:** Background tasks or services attempting to run before the database connection pool is warmed up.
- **Tight Coupling:** No clean way to enable or disable features (like a Search plugin or Caching) without manually hacking the core entry file.

## The ZCore Elegance
ZCore provides a declarative bootstrap structure via the `MAIN_PY_TEMPLATE` [cli/templates.py]. Instead of writing procedural logic, you configure the `Kernel`, register your domain `Plugins`, and attach core architectural Middlewares. The `main.py` serves strictly as an **Orchestrator**, ensuring infrastructure is ready before any domain logic begins.

=== "ZCore Declarative main.py"
        :::python
        from fastapi import FastAPI
        from zcore import Kernel, settings
        from zcore.web import RequestLogMiddleware, ScopedDependencyMiddleware
        from zcore.db import db_manager, register_db_event_dispatcher
        from zcore.logging import setup_logging

        # 1. Warm up Infrastructure
        setup_logging()
        db_manager.init_app(db_url=settings.DATABASE_URL)

        # 2. Initialize Kernel & Event Bridge
        kernel = Kernel()
        register_db_event_dispatcher(kernel.dispatcher)

        # 3. Create App with Kernel Lifespan
        app = FastAPI(title=settings.PROJECT_NAME, lifespan=kernel.lifespan)

        # 4. Bind Plugins & Middleware
        kernel.setup(app)
        app.add_middleware(RequestLogMiddleware)
        app.add_middleware(ScopedDependencyMiddleware)

=== "Standard FastAPI Procedural"
        :::python
        # Standard projects mix infra and business logic procedurally
        app = FastAPI()

        @app.on_event("startup")
        async def startup():
            # Manual, fragile ordering
            await init_logging()
            await init_db()
            # What if this fails? Is the error caught?
            await some_service_warmup()

        # Router includes are often scattered
        from orders.routers import router as orders_router
        app.include_router(orders_router)

        # Middleware ordering is manual and invisible
        app.add_middleware(MyMiddleware)

---

## Boundaries & Integration
The entry point is designed to wrap FastAPI's power without obscuring its standard API.

- **Native App Instance:** The `app` variable is a standard `FastAPI()` instance. You can use any native FastAPI decorator (`@app.get`) or feature directly in `main.py` without restriction.
- **Middleware Freedom:** ZCore provides `RequestLogMiddleware` and `ScopedDependencyMiddleware` for architectural stability, but you can add any third-party Starlette/FastAPI middleware using the standard `app.add_middleware()` method.
- **Plugin Decoupling:** You can add or remove domain modules simply by calling `kernel.add_plugin(MyModulePlugin())`. The Kernel handles the routing registration and startup logic internally.

---

## Under-the-Hood Spec

### 1. The DB-Event Dispatcher Bridge
A unique architectural feature is `register_db_event_dispatcher(kernel.dispatcher)` [db/events.py]. This creates a secure link between low-level database lifecycle events (like transaction commits) and the high-level application `EventDispatcher`. It allows domain handlers to respond to database changes in a non-blocking, loosely coupled manner.

### 2. Path Injection for Modular Imports
ZCore's `main.py` template includes a `sys.path.insert(0, ...)` block [cli/templates.py]. This ensures that your modular apps (generated via `zc startapp`) are discoverable as top-level modules, preventing complex relative import issues common in multi-directory FastAPI structures.

### 3. Integrated Exception Handling
The entry point registers the `app_exception_handler` [exceptions/handlers.py]. This ensures that any `AppException` (EntityNotFound, ValidationError, etc.) raised deep within a Service or Repository is caught at the boundary, logged with structured metadata, and returned in the standardized `ResponseWrapper` JSON envelope.

!!! info "Middleware Ordering"
    In ZCore, `RequestLogMiddleware` should generally be added first to ensure the entire request duration (including DI resolution time) is captured and a correlation ID is generated before any other logic executes.