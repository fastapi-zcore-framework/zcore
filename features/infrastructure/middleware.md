# ASGI Lifecycle Coordination

Trace every transaction with correlation IDs and manage request-scoped state boundaries for safe dependency resolution.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>ASGI Middleware</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Status</span><br>
    <strong>Recommended Core</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Underlying Tech</span><br>
    <strong>Starlette / contextvars / structlog</strong>
  </div>
</div>

## The Challenge
Maintaining observability and data integrity in an asynchronous environment presents unique challenges:
1.  **Disconnected Logs:** Without a Correlation ID (Request ID), tracking a single user's request journey through multiple service layers in a log aggregator is nearly impossible.
2.  **Session Leakage:** Improperly managed database sessions can lead to connection leaks or, worse, different services within the same request accidentally using different transactions.
3.  **Manual Context Passing:** Developers often find themselves passing a "context" dictionary or a raw database session object through every function call just to ensure a shared state.

## The ZCore Elegance
ZCore provides a duo of high-performance ASGI middlewares that automate these concerns at the entry point. `RequestLogMiddleware` ensures every request is uniquely identifiable and timed, while `ScopedDependencyMiddleware` initializes a secure execution boundary where the database session and other scoped dependencies are automatically shared and cleaned up.

=== "ZCore Middleware Registration"
        :::python
        from zcore.web import RequestLogMiddleware, ScopedDependencyMiddleware

        # Standard order in main.py
        app.add_middleware(RequestLogMiddleware)
        app.add_middleware(ScopedDependencyMiddleware)

=== "FastAPI Manual Management"
        :::python
        # Replicating ZCore's tracing and scoping manually:
        @app.middleware("http")
        async def trace_and_scope(request: Request, call_next):
            request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
            # Manually bind to logger
            # Manually start a timer
            # Manually open a DB session
            async with session_factory() as session:
                # How do we pass this session to nested services
                # without passing it as an argument everywhere?
                response = await call_next(request)
                return response

---

## Boundaries & Integration
ZCore Middlewares follow the standard Starlette/ASGI protocol, ensuring they play well with the rest of the ecosystem.

*   **Standard ASGI:** Both components are pure ASGI implementations. You can use them in any FastAPI, Starlette, or even raw ASGI application.
*   **Structlog Integration:** `RequestLogMiddleware` is designed to work with ZCore's structured logging. It automatically binds the `request_id` to `structlog.contextvars`, making it visible in every log line generated during that request.
*   **Bypass:** If you prefer a different logging or session management strategy, you can simply omit these middlewares. ZCore's internal components (like `Inject`) will still function, but "Scoped" lifecycles will fallback to "Transient" behavior if no active scope is detected.

---

## Under-the-Hood Spec

### 1. Hardened Correlation IDs
The `RequestLogMiddleware` uses a strict regex pattern (`REQUEST_ID_PATTERN`) to validate incoming `x-request-id` headers [web/middleware.py]. If a header is present but malformed or too long, ZCore rejects it and generates a fresh `uuid4` instead. This prevents header-injection attacks or bloated log metadata.

### 2. The `send_wrapper` Interceptor
ZCore doesn't just log the request ID; it ensures the client receives it back. The middleware wraps the ASGI `send` callable [web/middleware.py]. When the application starts sending the response (`http.response.start`), ZCore intercepts the event and appends the `x-request-id` to the outgoing headers, facilitating easier frontend-to-backend debugging.

### 3. Atomic Scope Cleanup
`ScopedDependencyMiddleware` generates a unique `scope_id` for every request and sets it in a `contextvar` [web/middleware.py]. Most importantly, it creates a database session using `db_manager.session()` and registers it as a scoped instance in the DI container. The `finally` block guarantees that `container.clear_scope(scope_id)` is called even if the request crashes, ensuring zero memory leaks or hanging DB connections.

### 4. Precision Timing
Logging uses `time.perf_counter()` to calculate the `duration_ms` [web/middleware.py]. This provides sub-millisecond precision for performance monitoring, which is then logged alongside the HTTP method and path as a structured record.

!!! info "Middleware Ordering"
    It is recommended to place `RequestLogMiddleware` as the outermost layer to capture the total execution time, including the time spent in subsequent middlewares like `ScopedDependencyMiddleware`.