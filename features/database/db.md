# Database Engine & Lifecycle

Centralized management for asynchronous connection pools and transactional session lifecycles.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>Infrastructure Layer</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Status</span><br>
    <strong>Core Requirement</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Underlying Tech</span><br>
    <strong>SQLAlchemy 2.0 / AsyncIO</strong>
  </div>
</div>

## The Challenge
Managing database connections in an asynchronous environment requires strict discipline. Without a centralized manager, developers often face:
- **Connection Leaks:** Forgetting to close sessions or dispose of engines, leading to exhausted database pools.
- **SQLite Incompatibility:** Passing standard pooling parameters (like `pool_size` or `max_overflow`) to a SQLite driver often raises errors or causes locking issues.
- **Manual Rollbacks:** Writing repetitive `try/except/rollback/finally` blocks in every route or service to ensure data integrity during failures.
- **DI Fragmentation:** Inconsistent methods of injecting the database session into different application layers.

## The ZCore Elegance
The `DatabaseManager` coordinates the entire SQLAlchemy lifecycle. It provides a unified `init_app` method that intelligently configures connection pools based on the database driver and exposes a thread-safe, asynchronous session factory. When combined with `SessionDep`, it ensures every request receives a cleanly managed transaction that is automatically rolled back on failure.

=== "ZCore Orchestration"
        :::python
        # 1. Initialize in main.py
        from zcore.db import db_manager, SessionDep

        db_manager.init_app(
            db_url="postgresql+asyncpg://user:pass@host/db",
            pool_size=20,
            echo=False
        )

        # 2. Inject anywhere (Router, Service, or Repo)
        @router.get("/data")
        async def get_data(db: SessionDep):
            # db is an active AsyncSession
            result = await db.execute(select(MyModel))
            return result.scalars().all()

=== "Standard SQLAlchemy Setup"
        :::python
        # Manual setup requires significant boilerplate
        engine = create_async_engine("...", pool_size=20)
        async_session = async_sessionmaker(engine, expire_on_commit=False)

        # Dependency for FastAPI
        async def get_db():
            async with async_session() as session:
                try:
                    yield session
                    # Manual commit might be needed here or in service
                except Exception:
                    await session.rollback()
                    raise
                finally:
                    await session.close()

        # And you must manually handle SQLite pool errors if switching envs

---

## Boundaries & Integration
ZCore's database layer provides a chassis for SQLAlchemy without obscuring its standard features.

*   **SQLAlchemy 2.0 Native:** The `AsyncSession` provided by `SessionDep` is a standard SQLAlchemy object. You can use any native feature (Queries, Mappers, Extensions) without restriction.
*   **IoC Resolved:** The `get_db` dependency retrieves the session from the ZCore `container`. This allows you to override the database session easily during integration tests using `app.dependency_overrides`.
*   **Engine Access:** While typically managed internally, the raw `AsyncEngine` is accessible via `db_manager._engine` for low-level operations like creating tables or running migration scripts.

---

## Under-the-Hood Spec

### 1. The SQLite Pool Bypass
Inside `init_app`, ZCore performs a driver check: `if "sqlite" not in db_url`. If the connection string points to SQLite, ZCore silently ignores `pool_size`, `max_overflow`, and `pool_recycle` parameters [db/setup.py]. This prevents the common "Unexpected argument" errors thrown by the SQLite driver while allowing the same configuration code to work across Dev (SQLite) and Prod (PostgreSQL).

### 2. Transactional Context Guard
The `db_manager.session()` context manager is built for safety [db/setup.py]. It wraps the session lifecycle in an `async with` block. If an unhandled exception occurs within that block, it explicitly calls `await session.rollback()` before propagating the error. This ensures that a failure in a service never leaves a transaction in a "hung" state.

### 3. Pre-configured Resilience
The engine is initialized with `pool_pre_ping=True` and `expire_on_commit=False` by default [db/setup.py]. `pool_pre_ping` prevents "Server has gone away" errors by testing the connection before use, while `expire_on_commit=False` allows you to access model attributes after a commit without triggering additional, often failing, lazy-load queries.

!!! info "Connection Recycling"
    ZCore defaults `pool_recycle` to 1800 seconds (30 minutes). This prevents stale connections from being terminated by database-side timeouts, which is especially important for long-running cloud SQL instances.