# 10-Minute Quickstart: Build a Task Manager API

Build a production-grade Task Manager API using ZCore in under 10 minutes. This guide covers the entire journey — from an empty directory to a running server with secure, scaffolded CRUD endpoints, dynamic field masking, and database persistence.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>Hands-On Tutorial</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Duration</span><br>
    <strong>~10 Minutes</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Difficulty</span><br>
    <strong>Beginner</strong>
  </div>
</div>

---

## What We're Building

A **Task Manager API** that supports:

- ✅ Automated creation, retrieval, updates, and deletion of tasks
- ✅ Built-in keyset (cursor) and offset pagination
- ✅ Advanced relational and conditional searches out-of-the-box
- ✅ Context-aware data masking to protect sensitive fields (like assignee emails)
- ✅ Scalable execution layers with structured lifecycle hooks

By the end, you'll have **7 fully functional endpoints** with namespaced authorization actions, running atop ZCore's Scoped Dependency Injection and Plugin lifecycle architecture.

---

## Step 1: Install & Initialize

Create a clean virtual environment and install the framework along with its database and cryptographic extras:

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install ZCore with all optional dependencies
pip install fastapi-zcore-framework[all]

# Initialize a new project
zc init taskmanager
cd taskmanager
```

The `zc init` command generates the following clean root structure:

```
taskmanager/
├── main.py              # Application entry point & orchestration
├── .env                 # Project environment settings (including secure SECRET_KEY)
├── requirements.txt     # Dependencies list
├── .gitignore           # Python, IDE, and DB exclusions
└── zcore_dev.db         # Local development SQLite database
```

---

## Step 2: Scaffold the Tasks Domain Module

ZCore enforces a **modular, domain-driven architecture**. Each feature context lives in its own directory, grouping its data model, projection schemas, persistence unit, business logic, and routing orchestrator into a single package.

Generate the `tasks` domain module using the built-in scaffolding tool:

```bash
zc startapp tasks --template
```

This commands scaffolds a clean, layered structure inside the `tasks` directory:

```
tasks/
├── __init__.py
├── models.py            # SQLAlchemy Declarative Model
├── schemas.py           # Context-Aware Zchema Definitions
├── repositories.py      # Persistence & Query Layer
├── services.py          # Pure Business Logic & Lifecycle Hooks
├── routers.py           # Scaffolded CRUD Router
└── plugin.py            # Kernel Lifespan Plugin Wrapper
```

Let's modify each component to build our task manager.

---

## Step 3: Define the Database Model

Open `tasks/models.py` and configure the database table schema. We will use modern SQLAlchemy 2.0 type mapping:

```python
import uuid
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from zcore import Base

class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(String(1024), default=None)
    priority: Mapped[str] = mapped_column(String(50), default="medium")
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    assignee_email: Mapped[str | None] = mapped_column(String(255), default=None)
```

!!! info "Auto-Generated Permission Scopes"
    By inheriting from `Base`, ZCore automatically exposes a descriptive `Actions` descriptor on the model based on its `__tablename__` [setup.py]:<br>
    - `Task.actions().CREATE`   &rightarrow; `"tasks:create"` <br>
    - `Task.actions().VIEW`     &rightarrow; `"tasks:view"` <br>
    - `Task.actions().UPDATE`   &rightarrow; `"tasks:update"` <br>
    - `Task.actions().DELETE`   &rightarrow; `"tasks:delete"` <br> 
    - `Task.actions().LISTVIEW` &rightarrow; `"tasks:listview"` <br>

---

### Step 4: Define Context-Aware Schemas

Open `tasks/schemas.py`. We will implement `Zchema` instead of Pydantic's raw `BaseModel` to handle data-masking at the serialization boundary:

```python
from pydantic import ConfigDict
import uuid
from zcore import Zchema

class TaskBase(Zchema):
    __model__ = "tasks"  # Binds schema to the "tasks" permission namespace

class TaskCreate(TaskBase):
    title: str
    description: str | None = None
    priority: str = "medium"
    assignee_email: str | None = None

class TaskUpdate(TaskBase):
    title: str | None = None
    description: str | None = None
    priority: str | None = None
    is_completed: bool | None = None
    assignee_email: str | None = None

class TaskResponse(TaskBase):
    id: uuid.UUID
    is_completed: bool

    model_config = ConfigDict(from_attributes=True)
```

!!! info "Unified Schema Projection & Mass Assignment Protection"
    In traditional FastAPI, developers suffer from "Schema Explosion"—creating separate classes like `TaskCreate`, `TaskUpdate`, `TaskPublicResponse`, and `TaskAdminResponse` just to handle field-level permissions. 
    
    With ZCore's `Zchema`, you can dramatically collapse this hierarchy [projection.py]. By defining a single, unified schema with all potential attributes, ZCore's `filter_restricted_inputs` and `secure_serializer` hooks automatically intercept requests [projection.py]. If `"tasks.assignee_email"` is added to the active `restricted_fields` context:
    1. **Input Shielding:** If a malicious user tries to POST or PUT `"assignee_email"`, ZCore silently prunes it *before* validation, preventing **Mass Assignment** exploits [projection.py].
    2. **Output Masking:** When returning data, ZCore automatically strips `"assignee_email"` from the JSON response before serialization, preventing **Data Leakage** [projection.py].
    
    This allows you to manage security dynamically at runtime using a single source of truth, rather than maintaining dozens of redundant Pydantic models.
---

## Step 5: Configure the Repository Layer

Open `tasks/repositories.py`. The repository abstracts raw database operations using the asynchronous SQLAlchemy engine:

```python
from zcore import BaseRepository
from sqlalchemy.ext.asyncio import AsyncSession
from .models import Task
from .schemas import TaskCreate, TaskUpdate

class TaskRepository(BaseRepository[Task, TaskCreate, TaskUpdate]):
    def __init__(self, db: AsyncSession):
        super().__init__(model=Task, db=db)
```

No query code is required. `BaseRepository` automatically provides high-performance implementations of `get`, `get_by_ids` (with instant fast-path validation), `get_list` (supporting offset & keyset cursors), `create`, `update`, `delete`, and `search` [repository.py].

---

## Step 6: Implement the Business Service

Open `tasks/services.py` to write your core business logic and lifecycle hooks:

```python
from zcore import BaseService, Inject
from .models import Task
from .schemas import TaskCreate, TaskUpdate
from .repositories import TaskRepository

class TaskService(BaseService[Task, TaskCreate, TaskUpdate]):
    def __init__(self, repository: TaskRepository = Inject(TaskRepository)):
        super().__init__(model=Task, repository=repository)

    # --- Lifecycle Hooks ---

    async def pre_create(self, schema: TaskCreate) -> None:
        """Executed automatically inside the write pipeline before DB insertion."""
        if schema.priority not in ["low", "medium", "high"]:
            schema.priority = "medium"

    async def post_create(self, model: Task) -> None:
        """Executed after successful DB insertion, prior to transaction commit."""
        # Clean boundary for publishing events, audit logs, or notifications
        pass
```

The `Inject(TaskRepository)` annotation instructs ZCore's **Scoped DI Container** to resolve the repository automatically within the active request context [di.py].

---

## Step 7: Scaffold the Automated Router

Open `tasks/routers.py`. We will extend `BaseRouter` to generate 7 secure CRUD and search endpoints:

```python
from zcore import BaseRouter
from .schemas import TaskCreate, TaskUpdate, TaskResponse
from .services import TaskService
from .models import Task

class TaskRouter(BaseRouter[TaskCreate, TaskUpdate]):
    model = Task
    create_schema = TaskCreate
    update_schema = TaskUpdate
    schema_out = TaskResponse
    service = TaskService
    
    prefix = "/tasks"
    tags = ["Tasks"]
    expose_schemas = True  # Activates runtime schema introspection

# Instantiate for plugin integration
router_instance = TaskRouter()
```

By default, the router uses `ZCoreAPIRoute` to ensure responses are serialized using our custom high-performance encoder, automatically appending the `Vary` HTTP header to prevent caching leaks when field masking is active [api_router.py].

---

## Step 8: Package as a Kernel Plugin

Open `tasks/plugin.py`. This class packages the `tasks` domain and defines its startup and shutdown dependencies:

```python
from fastapi import FastAPI
from zcore import Plugin
from .routers import router_instance

class TaskPlugin(Plugin):
    name = "tasks"
    version = "0.1.0"
    dependencies = []  # Declare other plugin names that must boot up first

    def setup(self, app: FastAPI) -> None:
        # Mount the scaffolded APIRouter instance to the FastAPI app
        app.include_router(router_instance.router)

    async def on_startup(self) -> None:
        """Standard startup lifecycles (e.g. warming up caches)"""
        pass

    async def on_shutdown(self) -> None:
        """Graceful cleanup tasks during application teardown"""
        pass
```

---

## Step 9: Wire the App in `main.py`

Open your root `main.py` file. This acts as the declarative orchestrator of the entire stack:

```python
from fastapi import FastAPI
from zcore import Kernel, settings
from zcore.web import RequestLogMiddleware, ScopedDependencyMiddleware
from zcore.exceptions import app_exception_handler, AppException
from zcore.db import db_manager, register_db_event_dispatcher
from zcore.logging import setup_logging

from tasks.plugin import TaskPlugin

# 1. Initialize structured logging configuration
setup_logging()

# 2. Configure the database connection pool (SQLite development fallback)
db_manager.init_app(
    db_url=settings.DATABASE_URL,
    echo=(settings.ENVIRONMENT == "development")
)

# 3. Create the Kernel and register domain plugins
kernel = Kernel()
kernel.add_plugin(TaskPlugin())

# 4. Bridge database events to the central kernel dispatcher
register_db_event_dispatcher(kernel.dispatcher)

# 5. Create FastAPI app bound to ZCore's topological lifespan
app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=kernel.lifespan
)

# 6. Finalize kernel plugin setups
kernel.setup(app)

# 7. Add core architectural middlewares & exception handlers
app.add_middleware(RequestLogMiddleware)
app.add_middleware(ScopedDependencyMiddleware)
app.add_exception_handler(AppException, app_exception_handler)
```

---

## Step 10: Run and Verify

Launch the development server with automated reload tracking:

```bash
zc run
```

```
📡 Starting ZCore Dev Server on 127.0.0.1:8000...
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

Open a new terminal session and test the scaffolded endpoints:

=== "1. Create a Task"

        :::bash
        curl -X POST http://127.0.0.1:8000/tasks/ \
          -H "Content-Type: application/json" \
          -d '{
            "title": "Evaluate ZCore Framework",
            "description": "Thoroughly test repository patterns and field masking",
            "priority": "high",
            "assignee_email": "architect@zcore.io"
          }'
        
        ========= Structured Response Envelope: =========
        {
          "success": true,
          "message": "Success",
          "data": {
            "id": "e8a93cb4-5fa7-4f67-a068-d06e2ea851c2",
            "title": "Evaluate ZCore Framework",
            "description": "Thoroughly test repository patterns and field masking",
            "priority": "high",
            "assignee_email": "architect@zcore.io",
            "is_completed": false
          },
          "meta": null
        }

=== "2. Paginated Query (GET)"

        :::bash
        curl http://127.0.0.1:8000/tasks/
        
        ========= Response =========
        {
          "success": true,
          "message": "Success",
          "data": [
            {
              "id": "e8a93cb4-5fa7-4f67-a068-d06e2ea851c2",
              "title": "Evaluate ZCore Framework",
              "description": "Thoroughly test repository patterns and field masking",
              "priority": "high",
              "assignee_email": "architect@zcore.io",
              "is_completed": false
            }
          ],
          "meta": null
        }

=== "3. Secure Schema Extraction"

    To generate dynamic forms on your frontend without exposing restricted structures, fetch the OpenAPI JSON Schema directly from the endpoint via `?schema=true`:

        :::bash
        curl http://127.0.0.1:8000/tasks/?schema=true
        
        ========= Context-Aware Schema Response: =========
        {
          "success": true,
          "message": "Schema generated successfully",
          "data": {
            "title": "TaskResponse",
            "type": "object",
            "properties": {
              "title": { "type": "string" },
              "description": { "type": "string" },
              "priority": { "type": "string", "default": "medium" },
              "assignee_email": { "type": "string" },
              "id": { "type": "string", "format": "uuid" },
              "is_completed": { "type": "boolean" }
            },
            "required": ["title", "id", "is_completed"]
          },
          "meta": {
            "restricted_fields": []
          }
        }

---

## Comparison Summary

| Built-In Feature Layer | ZCore Code Volume | Standard FastAPI Equivalent |
| :--- | :--- | :--- |
| **Declarative Model** | ~12 lines (`models.py`) | ~12 lines |
| **Masking Schemas** | ~20 lines (`schemas.py`) | ~70 lines (Separate models per-role) |
| **Persistence Repos** | ~5 lines (`repositories.py`) | ~90 lines (Manual connection and queries) |
| **Orchestrated Service**| ~15 lines (`services.py`) | ~60 lines (Manual context and commits) |
| **CRUD Router** | ~12 lines (`routers.py`) | ~120 lines (Routing, auth, and pagination) |
| **Plugin Registry** | ~12 lines (`plugin.py`) | N/A (Main file spaghetti) |
| **Total Footprint** | **~76 lines** | **~350+ lines** |

ZCore not only saves hundreds of lines of repetitive code, but it also natively enforces **thread-safe scoping**, **automated permission mappings**, **transactional safety**, and **real-time field masking** across your entire ecosystem.