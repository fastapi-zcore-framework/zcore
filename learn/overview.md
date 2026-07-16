# Overview

Standardize your development without sacrificing the freedom of FastAPI. ZCore provides the architectural "chassis" for your application, coordinating dependencies, security context, and database transactions into a unified, predictable lifecycle.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>Architectural Layer</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Status</span><br>
    <strong>Recommended Core</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Underlying Tech</span><br>
    <strong>FastAPI / Starlette</strong>
  </div>
</div>

## The Challenge
While FastAPI is exceptional for building high-performance APIs, it provides no structural blueprint. As projects scale, developers often encounter:
- **Global Dependency Clutter:** Difficulty managing different lifecycles (Singleton vs. Scoped) across modules.
- **Transactional Inconsistency:** Scattered database commits leading to partial data writes.
- **Security Boilerplate:** Manual field masking and permission checks repeated across dozens of routes.
- **Plugin Fragmentation:** Hard-to-track initialization orders for background workers, caches, and database engines.

## The ZCore Elegance
ZCore solves this by introducing a **Plugin-based Kernel**. Instead of manually wiring everything in a bloated `main.py`, you register domain-specific plugins. ZCore calculates the correct initialization order and manages the application lifespan automatically.

=== "`ZCore Plugin Orchestration`"

        :::python
        # Define a clean, isolated plugin for your domain
        class PaymentPlugin(Plugin):
            name = "payments"
            dependencies = ["database", "auth"] # ZCore sorts these automatically

            def setup(self, app: FastAPI):
                app.include_router(payment_router)

            async def on_startup(self):
                await payment_gateway.connect()

        # In your main.py: Simple, declarative registration
        kernel = Kernel()
        kernel.add_plugin(PaymentPlugin())
        app = FastAPI(lifespan=kernel.lifespan)
        kernel.setup(app)

=== "`Standard FastAPI Manual Setup`"

        :::python
        # Standard FastAPI requires manual, sequential ordering in main.py
        app = FastAPI()

        @app.on_event("startup")
        async def startup():
            # Manual ordering: If database isn't ready, payment fails.
            # This becomes a "main.py" file with 500+ lines in large projects.
            await init_db()
            await init_auth()
            await payment_gateway.connect()
        
        app.include_router(payment_router)
        app.include_router(auth_router)
        # ... and 20 other routers

---

## The Unified Request Journey
ZCore coordinates the request lifecycle through specialized middlewares and context managers, ensuring that every coroutine knows the current user and their data restrictions.

<p align="center">
  <img src="https://raw.githubusercontent.com/fastapi-zcore-framework/zcore/master/docs/assets/overview.png" 
  alt="The Unified Request Journey" width="700">
</p>

---

## Boundaries & Integration
ZCore is designed as a **complementary chassis**. It does not hide FastAPI; it stabilizes it.

*   **Pydantic Compatibility:** `Zchema` inherits directly from Pydantic's `BaseModel`. You can use standard Pydantic features (validators, computed fields) exactly as you always have.
*   **Starlette Middlewares:** ZCore middlewares are standard ASGI/Starlette implementations. You can mix them with any other third-party FastAPI middleware.
*   **Bypass Strategy:** If you have a route that doesn't fit the `BaseRouter` pattern, you can write a standard FastAPI `@app.get("/")` path function. You can still use `Inject()` to retrieve services or repositories from the ZCore container within that function.

---

## Under-the-Hood Spec

### 1. Topological Dependency Resolution
The Kernel uses `graphlib.TopologicalSorter` to analyze the `dependencies` attribute of every registered plugin. This builds a Directed Acyclic Graph (DAG), ensuring that if Plugin B depends on Plugin A, Plugin A's `on_startup` always completes before Plugin B begins.

### 2. High-Performance Reflection Cache
The Dependency Injection (DI) container utilizes a signature cache. During the first resolution of a class, ZCore uses the `inspect` module to analyze constructor type hints. This metadata is cached, allowing subsequent resolutions to skip reflection overhead entirely.

### 3. Contextual Isolation
ZCore utilizes Python's `contextvars` to maintain thread-safe and coroutine-safe state. The `request_context` manager ensures that `current_user_id` and `restricted_fields` are never leaked between concurrent requests, even in a high-concurrency async environment.