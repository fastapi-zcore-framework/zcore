# Framework Engine & Orchestration

The central nervous system coordinating plugin lifecycles, dependency resolution, and modular application transitions.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>Core Orchestrator</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Status</span><br>
    <strong>Core Infrastructure</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Underlying Tech</span><br>
    <strong>graphlib / Protocol</strong>
  </div>
</div>

## The Challenge
As FastAPI projects grow, the initialization sequence becomes a "procedural soup" inside `main.py`. Developers often encounter:
1.  **Race Conditions:** A service attempting to warm up a cache before the database connection pool is initialized.
2.  **Circular Import Deadlocks:** Modules importing each other's setup functions during startup.
3.  **Missing Requirements:** An application starting partially even when critical infrastructure (like a message broker plugin) failed to register.
4.  **Tear-down Leaks:** External connections (Redis, DB) not being closed in the correct order during shutdown, causing hanging processes.

## The ZCore Elegance
The `Kernel` manages the application through a **Topological Plugin System**. Every architectural unit is treated as a `Plugin` with declared dependencies. The Kernel calculates the mathematically correct initialization order using a Directed Acyclic Graph (DAG), ensuring every component is ready before the next one starts.

=== "ZCore Topological Plugins"
        :::python
        from zcore import Plugin, Kernel

        class PaymentPlugin(Plugin):
            name = "payments"
            # Explicitly wait for DB and Logging
            dependencies = ["db", "logging"]

            def setup(self, app: FastAPI):
                app.include_router(payment_router)

            async def on_startup(self):
                await gateway.connect()

        # Kernel sorts and executes in the right order
        kernel = Kernel()
        kernel.add_plugin(PaymentPlugin())
        kernel.add_plugin(DatabasePlugin()) # name="db"

=== "FastAPI Procedural Lifespan"
        :::python
        # Manual ordering is fragile and hard to track
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # You must manually ensure 'db' is before 'payments'
            await init_db()
            await init_logging()
            
            # If this is moved up by mistake, the app crashes
            await gateway.connect()
            yield
            # Manual shutdown is also tedious
            await gateway.close()
            await db.close()

---

## Boundaries & Integration
The Kernel is a thin orchestration layer that respects the native FastAPI lifecycle.

*   **Native Lifespan:** The `kernel.lifespan` method is a standard Python `@asynccontextmanager`. It is passed directly to the `FastAPI` constructor, meaning the framework follows the standard Starlette execution path.
*   **Protocol-Based:** You don't need to inherit from a specific ZCore class; as long as your object satisfies the `Plugin` protocol (having `name`, `version`, `dependencies`, and lifecycle methods), the Kernel will accept it [kernel/plugins.py].
*   **Bypass:** If a small part of your app doesn't need modularity, you can still register routes or logic directly in `main.py` using standard FastAPI methods—ZCore will ignore these and only manage the registered plugins.

---

## Under-the-Hood Spec

### 1. DAG-Based Dependency Resolution
The Kernel utilizes Python's `graphlib.TopologicalSorter` to analyze the `dependencies` list of every plugin [kernel/engine.py]. If Plugin A requires Plugin B, the sorter ensures B is processed first. If a circular dependency is detected (e.g., A -> B and B -> A), ZCore raises a `CycleError` during the `setup` phase, preventing the application from starting in an unstable state.

### 2. Reverse-Topological Shutdown
Resource management requires a "First In, Last Out" approach. The Kernel ensures that the `on_shutdown` hooks are executed in the **reverse order** of the startup sequence [kernel/engine.py]. This ensures that shared resources (like the Database) are only closed after the domain modules that depend on them have finished their cleanup tasks.

### 3. Missing Dependency Assertion
During the resolution phase, the Kernel cross-references every declared dependency name against the active registry [kernel/engine.py]. If a plugin declares a dependency that hasn't been registered in the `Kernel`, ZCore halts initialization with a `RuntimeError`, identifying the exact missing dependency by name.

### 4. Triple-Wave Startup
The Kernel executes startup logic in three distinct, sequential waves across all sorted plugins to ensure total system stability [kernel/engine.py]:
1.  **`before_startup`**: Verification and pre-checks.
2.  **`on_startup`**: Primary resource initialization.
3.  **`after_startup`**: Post-initialization signaling or background task spawns.

!!! info "Kernel Events"
    The Kernel automatically initializes a central `EventDispatcher` and registers it as a singleton in the DI container during the `setup` phase. This allows plugins to communicate through loosely coupled events without direct imports.