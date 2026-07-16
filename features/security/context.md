# Thread-Safe Execution Context

Manage authenticated identities and data-masking policies across asynchronous boundaries with zero state pollution.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>State Management</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Status</span><br>
    <strong>Core Core</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Underlying Tech</span><br>
    <strong>contextvars</strong>
  </div>
</div>

## The Challenge
In a high-concurrency asynchronous application, tracking the "current user" or active security policies is notoriously difficult. Developers often face:
1.  **Argument Drilling:** Passing a `user` object through five layers of service and repository calls just to log an ID or filter a query.
2.  **State Leakage:** Using standard global variables or thread-locals, which can leak data between concurrent requests in an `async/await` environment.
3.  **Inconsistent Validation:** Manually checking if a user ID is a valid UUID or if a list of restricted fields is mutable, leading to runtime errors in deep architectural layers.

## The ZCore Elegance
ZCore utilizes Python's `contextvars` to provide a coroutine-safe execution context. The `request_context` manager allows you to bind a user identity and a set of data-masking restrictions at the start of a request. These variables are then globally accessible to any downstream function (like a Search Engine or Repository) without being explicitly passed as arguments.

=== "ZCore Context Binding"
        :::python
        from zcore.context import request_context, get_current_user_id

        # 1. Bind context in a middleware or entry point
        with request_context(user_id="...", fields=["products.cost"]):
            # 2. Anywhere in your deep service/repository logic:
            uid = get_current_user_id()
            # uid is resolved automatically from the coroutine stack

=== "FastAPI Manual Passing"
        :::python
        # You must pass the user through every single function
        async def get_products(user_id: uuid.UUID, restricted: list[str]):
            return await repo.find_all(user_id, restricted)

        async def find_all(user_id: uuid.UUID, restricted: list[str]):
            # This becomes a maintenance nightmare in large apps
            query = select(Product).where(Product.owner_id == user_id)
            # ...

---

## Boundaries & Integration
ZCore Context is a low-level utility that bridges the gap between Web and Infrastructure layers.

*   **Native ContextVars:** ZCore uses standard `contextvars.ContextVar`. This means it integrates perfectly with standard Python logging (via `structlog`) and any other library that supports the `contextvars` protocol.
*   **Scoped Middleware:** The `ScopedDependencyMiddleware` automatically wraps every HTTP request in an empty context, ensuring a clean slate for every transaction.
*   **Bypass:** If you prefer explicit dependency injection, you can continue to pass `user` objects manually. ZCore's context is an *additional* capability, not a restrictive requirement.

---

## The Execution Flow

<p align="center">
  <img src="https://raw.githubusercontent.com/fastapi-zcore-framework/zcore/master/docs/assets/context.png" 
  alt="The Execution Flow" width="700">
</p>


---

## Under-the-Hood Spec

### 1. Token-Based Restoration Safety
ZCore context managers (`user_context`, `request_context`) utilize the `contextvars.Token` system [context/context.py]. When a context is set, a token is generated. Upon exiting the block, the state is **explicitly reset** to its previous value using this token. This guarantees that even if a request crashes or a task is recycled, the security context never "bleeds" into the next execution.

### 2. Immutable Restriction Sets
When you set `restricted_fields`, ZCore automatically converts the input into a `frozenset` [context/context.py]. This ensures that once fields are restricted for a request, they cannot be modified by downstream services, preventing accidental or malicious "unmasking" of sensitive data during a complex transaction.

### 3. Immediate UUID Integrity
The `set_current_user_id` function performs immediate type coercion [context/context.py]. If a string is provided, it is validated and converted to a `uuid.UUID` instance instantly. This ensures that downstream database queries never fail due to string-to-UUID comparison mismatches, moving the validation error to the very boundary of the request.

!!! info "Security Note"
    Context variables are isolated per asynchronous task. If you spawn a background task (e.g., `asyncio.create_task`), you must manually re-bind the context if the task requires the user's identity.