# Topological Domain Packaging

Structure your codebase into clean, self-contained modules with automated dependency resolution.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>Orchestration Protocol</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Status</span><br>
    <strong>Core Framework</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Underlying Tech</span><br>
    <strong>graphlib / typing.Protocol</strong>
  </div>
</div>

## The Challenge
As projects grow, the `main.py` file often becomes a "garbage bin" for initialization logic. Developers manually wire database connections, cache warmups, and route registrations. This leads to:
1.  **Circular Import Hell:** Modules trying to import each other during startup.
2.  **Race Conditions:** A service starting before the database connection is fully established.
3.  **Spaghetti Entry Points:** Hard-to-read setup code that requires manual ordering (e.g., Auth must load before Billing).
4.  **Tightly Coupled Logic:** Inability to easily enable or disable features (like a Search plugin) without hacking the core app setup.

## The ZCore Elegance
ZCore uses a **Topological Plugin System**. Every domain (Orders, Users, Payments) is packaged as a `Plugin`. Plugins declare their dependencies explicitly. The ZCore Kernel then calculates the mathematically correct startup order using a Directed Acyclic Graph (DAG). This ensures your architecture is decoupled, and every module starts only when its requirements are ready.

=== "ZCore Modular Plugin"
        :::python
        from zcore import Plugin
        from fastapi import FastAPI

        class InventoryPlugin(Plugin):
            name = "inventory"
            version = "1.0.0"
            dependencies = ["database", "logging"] # Declared requirements

            def setup(self, app: FastAPI):
                # Wire routers to the app
                from .routers import router
                app.include_router(router)

            async def on_startup(self):
                # Domain-specific startup logic
                await cache_warmer.warm_stock_levels()

            async def on_shutdown(self):
                await inventory_client.close()

=== "FastAPI Manual Sequencing"
        :::python
        # Standard main.py requires manual, fragile ordering
        app = FastAPI()

        @app.on_event("startup")
        async def startup():
            # You must manually remember the order:
            await init_logging()
            await init_db()
            # If you move this line up, the app might crash
            await cache_warmer.warm_stock_levels()

        app.include_router(inventory_router)
        # 500 lines of wiring later...

---

## Boundaries & Integration
ZCore Plugins are wrappers, not cages. They act as "Initialization Anchors" for standard FastAPI components.

*   **Standard FastAPI Routes:** The `setup(app)` method receives the raw `FastAPI` instance. You use standard `app.include_router()` or `app.add_middleware()` calls exactly as you would in a normal project.
*   **Decoupled Lifecycle:** You can write a Plugin that only handles background tasks without having any routes, or a Plugin that only registers Global Middlewares.
*   **Manual Bypass:** If a module is too simple to warrant a Plugin, you can still register its routes directly in `main.py` using standard FastAPI methods. However, it will not benefit from ZCore's topological startup ordering.

---

## Under-the-Hood Spec

### 1. Topological Sorting (DAG)
The ZCore Kernel utilizes Python's `graphlib.TopologicalSorter` [kernel/engine.py]. When `kernel.setup(app)` is called, it builds a graph where nodes are plugin names and edges are their `dependencies`. If a cycle is detected (e.g., A depends on B, and B depends on A), ZCore raises a `RuntimeError` immediately at startup to prevent unstable execution.

### 2. Runtime Protocol Validation
The `Plugin` interface is defined as a `runtime_checkable` Protocol [kernel/plugins.py]. This allows ZCore to verify that your classes implement the required attributes (`name`, `version`, `dependencies`) and methods without requiring strict class inheritance, though inheriting from `zcore.Plugin` is recommended for type safety.

### 3. Sequential Lifecycle Phases
The Kernel executes startup logic in three distinct, sequential waves across all sorted plugins [kernel/engine.py]:
1.  **`before_startup`**: Early-stage configuration or environment checks.
2.  **`on_startup`**: Core initialization (e.g., DB connections, Cache priming).
3.  **`after_startup`**: Post-init tasks (e.g., sending "System Up" notifications).
During shutdown, plugins are processed in **reverse topological order** to ensure that shared resources (like the Database) are closed only after the modules depending on them have safely shut down.

### 4. Dependency Integrity Check
Before starting, ZCore verifies that every string in a plugin's `dependencies` list corresponds to an actually registered plugin [kernel/engine.py]. If a dependency is missing, ZCore aborts the startup and logs exactly which plugin is missing its requirement.