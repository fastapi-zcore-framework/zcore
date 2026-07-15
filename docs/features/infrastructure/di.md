# Scoped Dependency Injection

Manage object lifecycles and resolve complex dependency graphs through thread-safe, constructor-based injection.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>Inversion of Control (IoC)</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Status</span><br>
    <strong>Core Infrastructure</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Underlying Tech</span><br>
    <strong>contextvars / Reflection</strong>
  </div>
</div>

## The Challenge
In standard FastAPI, dependencies are primarily resolved at the route level via `Depends()`. While powerful, this leads to:
1.  **Signature Bloat:** Passing the same 5 dependencies through every function layer (Router -> Service -> Repository).
2.  **Lifecycle Confusion:** Difficulty maintaining "Request-Scoped" objects (like a database session) consistently across multiple nested services.
3.  **Tight Coupling:** Classes manually instantiating their dependencies, making units hard to mock during testing.
4.  **Circular References:** No built-in protection against recursive dependency loops during instantiation.

## The ZCore Elegance
ZCore provides a central `IoCContainer` that supports **Singleton**, **Scoped**, and **Transient** lifecycles. It uses constructor-based injection—meaning your services and repositories simply declare their needs in `__init__`. ZCore analyzes the signatures, resolves the graph, and detects circular dependencies before your code even executes.

=== "ZCore Constructor Injection"
        :::python
        from zcore import Inject

        class PaymentService:
            # Dependencies are declared in the constructor
            def __init__(
                self, 
                repo: PaymentRepository, 
                notify: EmailService
            ):
                self.repo = repo
                self.notify = notify

        # In the Router: Zero manual wiring
        @router.post("/")
        async def pay(service: PaymentService = Inject(PaymentService)):
            return await service.process()

=== "FastAPI Raw Implementation"
        :::python
        # Dependencies must be manually passed through every layer
        @router.post("/")
        async def pay(
            db: AsyncSession = Depends(get_db),
            email_client: EmailClient = Depends(get_email_client)
        ):
            # Manual instantiation or repetitive Depends()
            repo = PaymentRepository(db)
            notify = EmailService(email_client)
            service = PaymentService(repo, notify)
            return await service.process()
            

---

## Resolution Workflow
The IoC container follows a strict resolution path, checking lifecycles in order of persistence.

<p align="center">
  <img src="https://raw.githubusercontent.com/fastapi-zcore-framework/zcore/master/docs/assets/di.png" 
  alt="Resolution Workflow" width="700">
</p>

---

## Boundaries & Integration
ZCore's DI system is a bridge between standard Python classes and the FastAPI ecosystem.

*   **FastAPI `Depends` Wrapper:** The `Inject()` function is a lightweight wrapper. It returns a FastAPI `Depends` object, ensuring full compatibility with FastAPI's native dependency tree and OpenAPI generation.
*   **Web-Independent:** The `container.resolve()` method can be used in CLI tools, background workers, or unit tests without an active HTTP request.
*   **Scoped Middleware:** Request-scoped dependencies (like `AsyncSession`) require the `ScopedDependencyMiddleware` to be active in `main.py`. This middleware initializes and clears the context-local storage for every request.

---

## Under-the-Hood Spec

### 1. High-Performance Signature Caching
ZCore avoids the runtime cost of Python reflection. The first time a class is resolved, the container uses `inspect.signature` and `typing.get_type_hints` to analyze its dependencies [kernel/di.py]. This metadata is stored in `_dependency_signature_cache`, allowing subsequent resolutions to skip the expensive introspection phase.

### 2. Circular Dependency Safeguard
During resolution, the container maintains a recursion `_stack` [kernel/di.py]. If the container attempts to resolve a class that is already present in the current resolution stack, it raises a `CircularDependencyError` with a clear trace (e.g., `A -> B -> C -> A`), preventing a stack overflow.

### 3. `Annotated` Metatype Resolution
The DI engine recognizes `typing.Annotated` during auto-wiring [kernel/di.py]. When a constructor parameter uses `Annotated[AsyncSession, Depends(get_db)]`, the engine strips the `Depends` wrapper by extracting the first argument of the `Annotated` origin using `get_args(annotation)[0]`. This allows ZCore to correctly resolve parameters typed with `Annotated` aliases like `SessionDep`, maintaining full compatibility with FastAPI's native dependency patterns.

### 4. Forward Reference Resolution
The DI engine utilizes `get_type_hints` rather than raw annotations. This allows ZCore to correctly resolve string-based forward references or `from __future__ import annotations` blocks, which standard `inspect` logic often fails to parse correctly.

### 5. Context Isolation
Scoped instances are stored using `contextvars` [kernel/di.py]. This ensures that even in highly concurrent async environments, two different requests never share the same "Scoped" object, while still allowing all services within the *same* request to share the same instance (e.g., the same Database Transaction).

### 6. The `get_db` Dependency & `SessionDep` Alias
ZCore exposes a `get_db` async generator and a `SessionDep` type alias for seamless database session injection [db/setup.py]. `get_db` calls `container.resolve(AsyncSession)` through the IoC container, returning the request-scoped session managed by `ScopedDependencyMiddleware`. `SessionDep` is defined as `Annotated[AsyncSession, Depends(get_db)]`, providing a clean, reusable type annotation:
```python
from zcore.db import SessionDep

@router.get("/items")
async def list_items(db: SessionDep):
    result = await db.execute(select(Item))
    return result.scalars().all()
```
This eliminates per-endpoint `Depends(get_db)` boilerplate while keeping the injection point explicit and type-checkable.

!!! info "Lifecycle Summary"
    - **Singleton:** Created once per application lifetime.
    - **Scoped:** Created once per HTTP request; shared across all services in that request.
    - **Transient:** A fresh instance is created every time it is requested.
