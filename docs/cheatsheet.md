# ZCore Framework Quick Reference (Cheat Sheet)

This cheat sheet serves as a quick-access reference guide for standard syntax, CLI commands, and configurations across the ZCore framework's 27 architectural layers and capabilities.

---

## Block 1: 🖥️ Bootstrapping & CLI

### 1. CLI Reference (`cli`)
The command-line utility for project scaffolding, application setup, and local development execution.

| Command | Example Usage | Description |
| :--- | :--- | :--- |
| `init` | `zc init billing_api` | Initializes a new ZCore project workspace. |
| `startapp` | `zc startapp checkout -t` | Scaffolds a new domain application with boilerplate code. |
| `run` | `zc run` | Launches the local reload-enabled development server. |
| `gensecret` | `zc gensecret` | Generates a secure, 64-character secret key. |

👉 [CLI Reference Documentation](features/infrastructure/cli.md)

---

### 2. Configuration (`config`)
Loads environmental configuration maps securely with fallback settings and lazy resolution through the settings proxy.

```python
from zcore.config import settings

# Lazy attribute resolution avoids premature instantiation during import time
db_url = settings.DATABASE_URL
token_lifespan = settings.ACCESS_TOKEN_EXPIRE_MINUTES
```

👉 [Configuration Reference Documentation](features/infrastructure/config.md)

---

### 3. Application Entry (`main.py`)
Bootstrapping boilerplate that brings together logging, dbs, routers, plugins, and the core lifecycle kernel.

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI
from zcore import Kernel, settings
from zcore.web import RequestLogMiddleware, ScopedDependencyMiddleware
from zcore.exceptions import app_exception_handler, AppException
from zcore.db import db_manager, register_db_event_dispatcher
from zcore.logging import setup_logging

setup_logging()
db_manager.init_app(db_url=settings.DATABASE_URL)

kernel = Kernel()
register_db_event_dispatcher(kernel.dispatcher)

app = FastAPI(title=settings.PROJECT_NAME, lifespan=kernel.lifespan)
app.add_middleware(RequestLogMiddleware)
app.add_middleware(ScopedDependencyMiddleware)
app.add_exception_handler(AppException, app_exception_handler)

kernel.setup(app)
```

👉 [Application Entry Reference Documentation](features/infrastructure/main.md)

---

## Block 2: 🧱 Modular App Architecture

### 4. DB Infrastructure (`db`)
Coordinates the database connection engine and registers table metadata for permission checking.

```python
from zcore.db import db_manager

# Initialize pool tuning and SQL query logging options
db_manager.init_app(db_url="sqlite+aiosqlite:///dev.db", pool_size=5, max_overflow=10, echo=True)
```

👉 [Database Infrastructure Reference Documentation](features/database/db.md)

---

### 5. Database Model (`db models`)
SQLAlchemy 2.0 declarative database model mapping, using UUIDv4 as the default identifier.

```python
import uuid
from sqlalchemy import String, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from zcore.db.setup import Base

class Product(Base):
    __tablename__ = "products"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
```

👉 [Database Model Reference Documentation](learn/1-db.md)

---

### 6. Pydantic Schemas (`schemas`)
Pydantic V2 payload definitions that enforce data type casting and load attributes directly from database mappers. All schemas should inherit from `Zchema` and declare a `__db_name__` for domain-bound security.

```python
from zcore import Zchema
from pydantic import Field, ConfigDict

class ProductResponse(Zchema):
    __db_name__ = "product"
    id: str
    name: str
    
    # Enables automatic mapping from database models
    model_config = ConfigDict(from_attributes=True)
```

👉 [Schemas Reference Documentation](learn/2-schemas.md)

---

### 7. Repository Layer (`repository`)
Data access layer that provides standard CRUD query operations directly with zero SQL boilerplate.

```python
from zcore.db.repository import BaseRepository
from zcore.db.setup import SessionDep
from .models import Product

class ProductRepository(BaseRepository[Product, ProductCreate, ProductUpdate]):
    def __init__(self, db: SessionDep):
        super().__init__(model=Product, db=db)
```

👉 [Repository Layer Reference Documentation](features/database/repository.md)

---

### 8. Business Service (`service`)
The business logic layer, featuring integrated dependency injection, `on_*` persistence methods, and pre/post lifecycle hooks.

```python
from zcore.service.base import BaseService
from zcore.kernel.di import Inject
from .repositories import ProductRepository
from .models import Product

class ProductService(BaseService[Product, ProductCreate, ProductUpdate]):
    def __init__(self, repository: ProductRepository = Inject(ProductRepository)):
        super().__init__(model=Product, repository=repository)
```

👉 [Business Service Reference Documentation](features/database/service.md)

---

### 9. Routing Scaffolding (`BaseRouter`)
A router class that automatically generates and secures all standard REST endpoints.

```python
from zcore.web import BaseRouter
from .schemas import ProductCreate, ProductUpdate, ProductResponse
from .services import ProductService
from .models import Product

class ProductRouter(BaseRouter[ProductCreate, ProductUpdate]):
    model = Product
    create_schema = ProductCreate
    update_schema = ProductUpdate
    schema_out = ProductResponse
    service = ProductService
    prefix = "/products"
```

👉 [Routing Scaffolding Reference Documentation](learn/5-router.md)

---

### 10. Plugin System (`Plugin`)
Packages modular components to handle initialization logic and coordinate application lifecycles.

```python
from fastapi import FastAPI
from zcore.kernel import Plugin

class ProductPlugin(Plugin):
    name = "products"
    version = "1.0.0"
    dependencies = []

    def setup(self, app: FastAPI) -> None:
        app.include_router(product_router)
        
    async def on_startup(self) -> None:
        pass # Handle startup tasks (e.g. warming caches)
```

👉 [Plugin System Reference Documentation](features/infrastructure/kernel.md)

---

### 11. Framework Core (`engine - kernel`)
The central engine that registers, topologically sorts, and triggers application modules during server startup.

```python
from zcore import Kernel
from products.plugin import ProductPlugin

kernel = Kernel()
# Register the plugin to include its modules during the startup phase
kernel.add_plugin(ProductPlugin())
```

👉 [Framework Core Reference Documentation](features/infrastructure/kernel.md)

---

## Block 3: 🔌 DI, Middlewares & Utilities

### 12. Dependency Injection (`di`)
Registers and resolves classes. It supports Scoped, Transient, and Singleton lifecycles.

```python
from zcore.kernel.di import container, Inject

# Register singleton
container.register_singleton(IMailer, SendGridMailer())

# Register scoped class (request lifetime)
container.register_scoped(IOrderRepository, SQLOrderRepository)

# Inject dependencies directly into constructors
def __init__(self, repo: IOrderRepository = Inject(IOrderRepository)):
    self.repo = repo
```

👉 [Dependency Injection Reference Documentation](features/infrastructure/di.md)

---

### 13. Kernel Events (`kernel - event`)
Subscribes to and dispatches events asynchronously, running listeners concurrently on the active event loop.

```python
from zcore.kernel.events import EventDispatcher

# Subscribe a listener to an event key
dispatcher.subscribe("order.created", send_invoice_email)

# Dispatch an event concurrently across all registered listeners
await dispatcher.dispatch("order.created", order_id="ord_102")
```

👉 [Kernel Events Reference Documentation](features/infrastructure/events.md)

---

### 14. ASGI Middlewares (`middleware`)
Configures tracing and sets up request-scoped memory environments to isolate concurrent requests.

```python
# Registered in main.py to handle request tracking and dependency isolation
app.add_middleware(RequestLogMiddleware)
app.add_middleware(ScopedDependencyMiddleware)
```

👉 [ASGI Middlewares Reference Documentation](features/infrastructure/middleware.md)

---

### 15. Utilities (`utils`)
Serializes non-primitive types and validates structures using JSON standard validation rules.

```python
from zcore.utils.helpers import json_dumps
from zcore.utils.jsonschema import validate_json_schema

# Serialize UUIDs, Decimals, and Dates cleanly
serialized_payload = json_dumps({"id": uuid.uuid4(), "amount": Decimal("10.50")})

# Validate data structures against a Draft-7 schema
validate_json_schema(data={"age": 20}, schema={"properties": {"age": {"type": "integer"}}})
```

👉 [Utilities Reference Documentation](features/infrastructure/utils.md)

---

## Block 4: 📊 Transactions, Search & Pagination

### 16. Multi-Repo Transactions (`uow`)
Executes transactional writes across multiple repositories in a single block, ensuring atomic changes.

```python
from zcore.db.uow import UnitOfWork

# Wrap multiple changes in a single database transaction
async with UnitOfWork(session, dispatcher) as uow:
    await order_repo.create(order_schema)
    await product_repo.update(product_id, update_schema)
    uow.register_event("checkout.completed", {"order_id": 102})
```

👉 [Multi-Repo Transactions Reference Documentation](features/database/uow.md)

---

### 17. Database Events (`db events`)
Signals database updates and dispatches them asynchronously, keeping transaction execution non-blocking.

```python
from zcore.db.events import dispatch_db_event

# Safely publish database events across the system
await dispatch_db_event("db.product.created", {"id": "prod_102"})
```

👉 [Database Events Reference Documentation](features/database/db-events.md)

---

### 18. DB Pagination (`pagination`)
Loads database records using either Offset-based pagination or keyset Cursor pagination.

```python
from zcore.db.pagination import PageNumberParams, CursorParams

# Offset parameters
offset_params = PageNumberParams(page=1, size=20, sort_by="price", sort_order="desc")

# Keyset parameters (using base64 encoded cursor positions)
cursor_params = CursorParams(cursor="eyJ2YWx1ZSI6MjAsImlkIjoyfQ==", size=25)
```

👉 [DB Pagination Reference Documentation](features/database/pagination.md)

---

### 19. Dynamic Search (`search`)
Builds complex database queries dynamically, validating paths and converting types securely.

```json
{
  "filters": [
    { "field": "stock", "op": "gt", "value": 10 },
    { "op": "or", "items": [
        { "field": "name", "op": "ilike", "value": "widget" },
        { "field": "price", "op": "le", "value": 100.00 }
    ]}
  ],
  "sort": [{ "field": "price", "order": "asc" }],
  "size": 15,
  "page": 1
}
```

👉 [Dynamic Search Reference Documentation](features/database/search.md)

---

## Block 5: 🛡️ Security, Context & Response Projection

### 20. Context Management (`context`)
Stores user and field restriction parameters securely across async execution blocks. Restricted fields use the `{db_name}.{field}` syntax for domain-bound security.

```python
from zcore.context import request_context, get_current_user_id

# Isolate user context and field restrictions for a specific block
with request_context(user_id=active_user_id, fields=["user.hashed_password"]):
    # Retrieve the active user ID within any nested function block
    current_user = get_current_user_id()
```

👉 [Context Management Reference Documentation](features/security/context.md)

---

### 21. Cryptographic Security (`security`)
Hashes passwords using the Argon2id algorithm and issues cryptographically signed JWT credentials.

```python
from zcore.security import get_password_hash, create_token

# Generate a secure Argon2id password hash
hashed_password = get_password_hash("raw-password-string")

# Issue a new signed JWT access token containing claims
token = create_token(data={"sub": "user_id_102", "role": "admin"})
```

👉 [Cryptographic Security Reference Documentation](features/security/security.md)

---

### 22. Custom Route Mechanics (`api-router`)
Enables custom routing rules, including dynamic schema exposure and native Zchema-based security.

```python
# Enables /route/?schema=true queries on the endpoint
expose_schemas = True
```

👉 [Custom Route Mechanics Reference Documentation](features/security/api-router.md)

---

### 23. Output Projection & Security (`Zchema & response`)
ZCore's `Zchema` base class automatically prunes restricted fields across schema generation, input validation, and response serialization — all without web-layer middleware.

```python
from zcore import Zchema
from zcore.web.response import ResponseWrapper

class EmployeeResponse(Zchema):
    __db_name__ = "employee"
    id: str
    name: str
    salary: float  # Automatically pruned for non-admin users

# Package responses in the standardized JSON envelope
response = ResponseWrapper.success_response(data=employee_data, message="Success")
```

👉 [Zchema Security Reference Documentation](features/security/zchema.md)

---

### 24. Global Exceptions (`exceptions`)
Standardizes custom application exception mappings and converts errors into clean JSON error responses.

```python
from zcore.exceptions.base import ValidationError, EntityNotFound

# Raise to return an HTTP 400 Bad Request response containing metadata
raise ValidationError(message="Validation failed", payload={"field": "email"})

# Raise to return an HTTP 404 Not Found response
raise EntityNotFound(message="Resource not found")
```

👉 [Global Exceptions Reference Documentation](features/security/exceptions.md)

---

## Block 6: 🌐 Advanced Ecosystem Services

### 25. Hybrid Caching (`cache`)
Caches data using local in-memory storage, falling back cleanly to Redis connections if available.

```python
from zcore.cache import BaseCache

cache = BaseCache[UserSchema](prefix="users")

# Set cache key
await cache.set(key="user_102", value=user_data, ttl=3600)

# Retrieve cached payload using Pydantic schema validation
cached_user = await cache.get("user_102", target_type=UserSchema)
```

👉 [Hybrid Caching Reference Documentation](features/ecosystem/cache.md)

---

### 26. File Storage (`storage`)
Manages file uploads securely, protecting against path traversal and validating files based on their Magic Bytes.

```python
from zcore.storage.local import LocalStorageProvider
from zcore.storage.validators import SafeMimeTypeValidator

# Initialize local storage provider with image magic-byte security validators
storage = LocalStorageProvider(
    base_path="./uploads",
    validators=[SafeMimeTypeValidator(allowed_mimes=["image/png", "image/jpeg"])]
)

# Upload and save file safely
saved_path = await storage.upload(file, folder="profile_pictures")
```

👉 [File Storage Reference Documentation](features/ecosystem/storage.md)

---

### 27. Event Streaming (`stream`)
Streams real-time updates over WebSocket channels, using Redis PubSub to route events across instances.

```python
from zcore.web.streams import StreamManager

stream_manager = StreamManager()

# Stream real-time events to a connected client
async with stream_manager.subscription(user_id) as queue:
    while True:
        event = await queue.get()
        await websocket.send_json(event)
```

👉 [Event Streaming Reference Documentation](features/ecosystem/stream.md)

---

!!! tip "Fast Scaffold Lookup"
    Use the `zc startapp <app_name> -t` CLI command to quickly generate templates pre-configured with standard models, schemas, repositories, services, and routers.