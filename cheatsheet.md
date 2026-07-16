# Pocket Reference & Cheat Sheet

A rapid lookup guide for ZCore's core components, common patterns, and CLI commands. Each section links to the full documentation for deeper context.

---

## Core Infrastructure

### Dependency Injection

| Concept | Usage |
|---|---|
| **IoCContainer** | `container = IoCContainer()` — Central registry for all DI lifecycles |
| **Inject** | `service: MyService = Inject(MyService)` — FastAPI-compatible DI wrapper |
| **Singleton** | `container.register_singleton(Interface, instance)` — One instance per app lifetime |
| **Scoped** | `container.register_scoped(Interface, Impl)` — One instance per HTTP request |
| **Transient** | `container.register_transient(Interface, Impl)` — New instance every resolution |
| **Reflection Cache** | `_dependency_signature_cache` — Caches `get_type_hints` results after first resolution |
| **Nested Dependencies** | Auto-wires recursive constructor graphs — `Service → Repository → Session` |
| **Annotated Support** | Resolves `Annotated[Type, ...]` by extracting the base type |
| **SessionDep** | `db: SessionDep` — `Annotated[AsyncSession, Depends(get_db)]` alias |
| **get_db** | `async def get_db()` — Resolves scoped `AsyncSession` from container |

[Full DI Documentation](features/infrastructure/di.md)

---

### Framework Engine (Kernel)

| Concept | Usage |
|---|---|
| **Plugin Protocol** | Class with `name`, `dependencies`, `setup()`, `on_startup()`, `on_shutdown()` |
| **Kernel** | `kernel = Kernel(); kernel.add_plugin(MyPlugin()); kernel.setup(app)` |
| **Lifespan** | `FastAPI(lifespan=kernel.lifespan)` — Auto-orders startup/shutdown via DAG |
| **Dependency Sort** | `graphlib.TopologicalSorter` — Ensures plugins init in correct order |
| **Missing Check** | Raises `RuntimeError` if a declared plugin dependency is not registered |

[Full Kernel Documentation](features/infrastructure/kernel.md)

---

### Kernel Events

| Concept | Usage |
|---|---|
| **EventDispatcher** | `await dispatcher.dispatch("event.name", key=value)` |
| **Subscribe** | `@dispatcher.subscribe("event.name")` — Decorate any sync/async handler |
| **Concurrent Execution** | `asyncio.gather(return_exceptions=True)` — All async handlers run in parallel |
| **Failure Isolation** | One handler exception never blocks other handlers |

[Full Events Documentation](features/infrastructure/events.md)

---

### ASGI Middlewares

| Concept | Usage |
|---|---|
| **RequestLogMiddleware** | `app.add_middleware(RequestLogMiddleware)` — Logs method, path, duration, correlation ID |
| **ScopedDependencyMiddleware** | `app.add_middleware(ScopedDependencyMiddleware)` — Initializes request-scoped DI context |
| **Correlation ID** | Auto-generated `x-request-id` header, validated against regex, returned in response |

[Full Middleware Documentation](features/infrastructure/middleware.md)

---

### Application Entry (main.py)

| Concept | Usage |
|---|---|
| **Bootstrap Order** | `setup_logging()` → `db_manager.init_app()` → `Kernel()` → `FastAPI(lifespan=...)` → `kernel.setup(app)` → middlewares |
| **Exception Handler** | `app.add_exception_handler(AppException, app_exception_handler)` |
| **DB-Event Bridge** | `register_db_event_dispatcher(kernel.dispatcher)` |

[Full Main Documentation](features/infrastructure/main.md)

---

### Configuration Settings

| Concept | Usage |
|---|---|
| **Settings Proxy** | `from zcore import settings` — Lazy-resolved, no circular imports |
| **Pydantic V2** | `ZCoreCoreSettings` inherits `pydantic_settings.BaseSettings` |
| **Lazy Resolution** | `settings.DATABASE_URL` — Resolved from IoC container on first access |
| **Env Switching** | `ENV_FILE=.env.test` — Dynamic `.env` file selection |

[Full Config Documentation](features/infrastructure/config.md)

---

### CLI Scaffolding

| Command | Description |
|---|---|
| `zc init <name>` | Create new project with secure `.env` and directory structure |
| `zc startapp <name>` | Scaffold a domain module (model, schema, repo, service, router, plugin) |
| `zc run` | Launch `uvicorn` with auto `PYTHONPATH` injection |
| `zc gensecret` | Generate a cryptographically secure 64-char secret key |

[Full CLI Documentation](features/infrastructure/cli.md)

---

### System Utilities

| Function | Description |
|---|---|
| `json_dumps(data)` | Serialize UUID, Decimal, datetime safely |
| `json_loads(data)` | Deserialize with enhanced type support |
| `slugify(text)` | URL-safe slug: `"ZCore Framework!"` → `"zcore-framework"` |
| `validate_json_schema(data, schema)` | Validate against Draft-7, raises `ValidationError` on failure |

[Full Utils Documentation](features/infrastructure/utils.md)

---

## Data & Transactions

### Database Manager

| Concept | Usage |
|---|---|
| **init_app** | `db_manager.init_app(db_url="postgresql+asyncpg://...")` |
| **SQLite Bypass** | Auto-ignores `pool_size`/`max_overflow` for SQLite connections |
| **Session Context** | `async with db_manager.session() as session:` — Auto rollback on exception |
| **Engine Access** | `db_manager._engine` — Raw `AsyncEngine` for migrations |

[Full DB Documentation](features/database/db.md)

---

### Repository Pattern

| Concept | Usage |
|---|---|
| **BaseRepository** | `class ProductRepo(BaseRepository[Product, CreateSchema, UpdateSchema])` |
| **Read/Write Mixins** | `get()`, `create()`, `update()`, `delete()`, `get_by_ids()` |
| **Exist Optimization** | `exists(**filters)` — Uses `SELECT 1` for fast boolean check |
| **Search** | `search(SearchRequest)` — Delegates to `SearchEngine` |

[Full Repository Documentation](features/database/repository.md)

---

### Business Services

| Concept | Usage |
|---|---|
| **BaseService** | `class ProductService(BaseService[Product, CreateSchema, UpdateSchema])` |
| **Safe Commit** | `await self._safe_commit()` — Context-aware, skips if UoW is active |
| **Lifecycle Hooks** | `after_create(obj)`, `after_update(obj)`, `after_delete(obj)` — Override for side effects |

[Full Service Documentation](features/database/service.md)

---

### Unit of Work

| Concept | Usage |
|---|---|
| **UoW** | `async with UnitOfWork(db_manager) as uow:` — Atomic transaction boundary |
| **Post-Commit Events** | `uow.add_event("event.name", **kwargs)` — Dispatched only after successful commit |
| **Isolation** | Multiple repos share the same transaction within a UoW block |

[Full UoW Documentation](features/database/uow.md)

---

### Database Events

| Concept | Usage |
|---|---|
| **dispatch_db_event** | `dispatch_db_event("event.name", session, **kwargs)` — Error-isolated propagation |
| **Registration** | `register_db_event_dispatcher(dispatcher)` — Bridges DB events to app-level dispatcher |

[Full DB Events Documentation](features/database/db-events.md)

---

### Pagination Engine

| Concept | Usage |
|---|---|
| **Cursor Pagination** | `CursorParams(cursor="base64string", size=20)` — Keyset-based, stable under writes |
| **Offset Pagination** | `PageNumberParams(page=1, size=20)` — Standard offset/limit |
| **Base64 Encoding** | Cursor is Base64-encoded for safe URL transport |
| **Count Optimization** | `order_by(None).count()` — Strips ordering for faster count queries |

[Full Pagination Documentation](features/database/pagination.md)

---

### Dynamic Search Engine

| Concept | Usage |
|---|---|
| **SearchRequest** | `SearchRequest(filters={...}, sorts=[...], eager_loads=[...])` |
| **JSON Query Builder** | Translates nested JSON filters to safe SQL WHERE clauses |
| **Depth Protection** | `max_depth` and `max_filters` — Prevents DoS via deeply nested queries |
| **Wildcard Escaping** | Auto-escapes `%` and `_` in LIKE patterns |

[Full Search Documentation](features/database/search.md)

---

## Security & Shielding

### Thread-Safe Context

| Concept | Usage |
|---|---|
| **request_context** | `with request_context(user_id=..., fields={"products.cost"}):` |
| **get_current_user_id()** | Returns `uuid.UUID` from active context |
| **get_restricted_fields()** | Returns `frozenset` of restricted field paths |
| **Token Reset** | Context uses `contextvars.Token` for safe restoration |

[Full Context Documentation](features/security/context.md)

---

### Cryptographic Protocols

| Concept | Usage |
|---|---|
| **Password Hashing** | `get_password_hash("pw")` — Argon2id (64MB memory, 3 iterations, 4 threads) |
| **Token Creation** | `create_token(data={"sub": id, "scopes": [...]})` — Auto-detects HS256 vs RS256 |
| **Production Guard** | Fatal `RuntimeError` if `SECRET_KEY` is default in production |
| **Asymmetric Detection** | Auto-switches to RS256 if `JWT_PRIVATE_KEY`/`JWT_PUBLIC_KEY` are set |

[Full Security Documentation](features/security/security.md)

---

### API Routing Mechanics

| Concept | Usage |
|---|---|
| **ZCoreAPIRoute** | `APIRouter(route_class=ZCoreAPIRoute)` — Custom route handler |
| **Schema Exposure** | `?schema=true` — Returns context-pruned JSON-Schema |
| **Vary Header** | Auto-appends `Vary: Authorization, Cookie` on pruned responses |
| **Response Preservation** | Custom `response_class` is never silently overwritten |

[Full API Router Documentation](features/security/api-router.md)

---

### Zchema Security & Schema Pruning

| Concept | Usage |
|---|---|
| **Zchema** | `class ProductBase(Zchema): __model__ = "products"` — Single schema, context-aware |
| **Input Pruning** | `model_validator(mode="before")` — Prevents mass assignment |
| **Output Pruning** | `model_serializer(mode="wrap")` — Strips restricted fields from responses |
| **Schema Pruning** | `__get_pydantic_json_schema__` — Hides restricted fields from `?schema=true` |

[Full Zchema Documentation](features/security/zchema.md)

---

### Centralized Exception Handler

| Exception | HTTP Code | Usage |
|---|---|---|
| `EntityNotFound` | 404 | `raise EntityNotFound("User not found")` |
| `DuplicateEntity` | 409 | `raise DuplicateEntity("Email already exists")` |
| `AuthError` | 401 | `raise AuthError("Invalid credentials")` |
| `ForbiddenError` | 403 | `raise ForbiddenError("Insufficient permissions")` |
| `ValidationError` | 400 | `raise ValidationError("Invalid input")` |

All exceptions return `ResponseWrapper` envelope with `error_type` and optional `payload`.

[Full Exceptions Documentation](features/security/exceptions.md)

---

## Advanced Ecosystem

### Distributed Caching

| Concept | Usage |
|---|---|
| **BaseCache** | `cache = BaseCache[ProductOut](prefix="products")` |
| **Get with Validation** | `await cache.get("key", target_type=ProductOut)` — Auto Pydantic validation |
| **Set with TTL** | `await cache.set("key", value, ttl=300)` |
| **Fallback** | Redis → local `TTLLRUCache` (maxsize=1000) on failure |
| **Eviction Loop** | Background task runs every 60s, purges expired local entries |

[Full Cache Documentation](features/ecosystem/cache.md)

---

### File Storage & Security

| Concept | Usage |
|---|---|
| **LocalStorageProvider** | `LocalStorageProvider(base_path="./uploads", validators=[...])` |
| **Validators** | `FileExtensionValidator`, `MaxFileSizeValidator`, `SafeMimeTypeValidator` |
| **Magic Bytes** | Reads first 2048 bytes, blocks PHP/HTML/MZ/Shebang patterns |
| **UUID Truncation** | Filenames use first 15 chars of `uuid4()` — collision-resistant |
| **Path Traversal Guard** | `is_relative_to()` check prevents `../../etc/passwd` attacks |

[Full Storage Documentation](features/ecosystem/storage.md)

---

### WebSocket Streaming

| Concept | Usage |
|---|---|
| **StreamManager** | `manager = StreamManager()` — Per-user queue management |
| **Subscribe** | `async with manager.subscription(user_id) as queue:` — Context manager with auto cleanup |
| **Publish** | `await manager.publish(user_id, {"type": "update", ...})` — Redis PubSub + local fallback |
| **Queue Protection** | `asyncio.Queue(maxsize=100)` — Overflowing queues are silently dropped |
| **Horizontal Scale** | All nodes share Redis PubSub pattern `stream:user:*` |

[Full Stream Documentation](features/ecosystem/stream.md)

---

## Quick CLI Reference

```bash
zc init my_project          # Create new project
zc startapp inventory       # Scaffold domain module
zc run                      # Start dev server
zc gensecret                # Generate secure secret key
zc --help                   # List all commands
```

---

## Common Patterns

### Scaffold a Full CRUD Module

```python
# 1. Model
class Product(Base):
    __tablename__ = "products"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str]

# 2. Schema
class ProductBase(Zchema):
    __model__ = "products"
    name: str

# 3. Repository
class ProductRepository(BaseRepository[Product, ProductBase, ProductBase]):
    def __init__(self, db: AsyncSession): super().__init__(model=Product, db=db)

# 4. Service
class ProductService(BaseService[Product, ProductBase, ProductBase]):
    def __init__(self, repository: ProductRepository = Inject(ProductRepository)):
        super().__init__(model=Product, repository=repository)

# 5. Router (auto-generates 7 endpoints)
class ProductRouter(BaseRouter[ProductBase, ProductBase]):
    model = Product
    create_schema = ProductBase
    update_schema = ProductBase
    schema_out = ProductBase
    service = ProductService
    prefix = "/products"
```

### Register Exception Handler

```python
from zcore.exceptions import AppException, app_exception_handler
app.add_exception_handler(AppException, app_exception_handler)
```

### Use SessionDep

```python
from zcore.db import SessionDep

@router.get("/items")
async def list_items(db: SessionDep):
    result = await db.execute(select(Item))
    return result.scalars().all()
```

### Dispatch an Event

```python
await dispatcher.dispatch("user.registered", user=user, timestamp=now)
```

### Use Unit of Work

```python
async with UnitOfWork(db_manager) as uow:
    user = await user_repo.create(data)
    await uow.add_event("user.registered", user_id=user.id)
# Event dispatched only after successful commit
```

---

!!! tip "Full Documentation"
    Each section above links to its complete documentation page. For the tutorial, see [Learn (Tutorial)](learn/overview/). For practical recipes, see [How-To Guides](how-to/auth-setup/).