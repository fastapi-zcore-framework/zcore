# Database Models & Metadata

Define your schema and auto-generate standardized permission scopes for every entity.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>Declarative Base</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Status</span><br>
    <strong>Core Requirement</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Underlying Tech</span><br>
    <strong>SQLAlchemy 2.0 Async</strong>
  </div>
</div>

## The Challenge
In large-scale FastAPI applications, managing authorization often becomes a "string-guessing" game. Developers manually define permission strings like `"product:view"` or `"order:delete"` in routers, while the models remain unaware of these scopes. This leads to **permission drift**, where a table is renamed or a scope is mistyped, resulting in silent authorization failures or security loopholes.

## The ZCore Elegance
ZCore's `Base` is a thin extension of SQLAlchemy's `DeclarativeBase`. It provides a centralized `.actions()` method that dynamically generates a structured `Actions` object based on the `__tablename__`. These actions are then used by ZCore routers and security layers to enforce consistent authorization without hardcoded strings.

=== "ZCore Model with Actions"
        :::python
        from zcore import Base
        from sqlalchemy.orm import Mapped, mapped_column
        import uuid

        class Product(Base):
            __tablename__ = "products"
            
            id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
            name: Mapped[str] = mapped_column()

        # ZCore automatically provides:
        # Product.actions().CREATE   -> "products:create"
        # Product.actions().VIEW     -> "products:view"
        # Product.actions().DELETE   -> "products:delete"
        # Product.actions().LISTVIEW -> "products:listview"

=== "Manual SQLAlchemy Approach"
        :::python
        # Standard SQLAlchemy models don't know about permissions.
        # You are forced to manually manage strings elsewhere:
        class Product(Base):
            __tablename__ = "products"
            id: Mapped[uuid.UUID] = mapped_column(primary_key=True)

        # In your security layer:
        PRODUCT_CREATE = "products:create" # Manual string
        PRODUCT_VIEW = "products:view"     # Manual string
        # High risk of typos and zero link to the actual model class.

---

## Boundaries & Integration
ZCore does not hide SQLAlchemy; it empowers it.

*   **Standard SQLA 2.0:** Because `Base` inherits from `DeclarativeBase`, you use the modern `Mapped` and `mapped_column` syntax exactly as documented in SQLAlchemy 2.0.
*   **Bypass:** If you do not wish to use ZCore's authorization system, you can still use the `Base` class for standard migrations and queries without ever calling `.actions()`.
*   **Custom Engines:** While `db_manager` provides a pre-configured `AsyncEngine`, you can still create your own SQLAlchemy engine and bind ZCore models to it—they are 100% compatible with standard `AsyncSession` operations.

---

## Under-the-Hood Spec

### 1. The `Actions` Dataclass
The `Actions` object is an immutable, frozen dataclass [setup.py]. When `Base.actions()` is called, ZCore iterates over the internal fields of the `Actions` class and interpolates the `__tablename__` to create unique, namespaced permission keys. This ensures that permission names are always derived directly from the source of truth—the database schema.

### 2. Intelligent Connection Pooling
The `DatabaseManager.init_app` method contains specific logic for SQLite vs. server-based databases (PostgreSQL/MySQL) [setup.py]. For SQLite, it disables `pool_size` and `max_overflow` to prevent locking issues common with file-based databases, while enabling high-performance connection pooling and `pool_pre_ping` for production-grade relational servers.

### 3. Lifecycle Awareness
ZCore models are designed to be used with the `db_manager.session()` context manager. This manager ensures that if an exception occurs during a database operation, `session.rollback()` is invoked automatically before the error is propagated, keeping your database state clean without manual `try/except` blocks in every service.