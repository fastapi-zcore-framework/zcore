<p align="center">
  <img src="https://raw.githubusercontent.com/fastapi-zcore-framework/zcore/master/docs/assets/banner.png" alt="ZCore Logo" width="620">
</p>

<p align="center">
  <strong>A pragmatic and complementary architectural layer built on top of FastAPI.</strong><br>
  <em>Standardize your structure, protect your data, and manage atomic transactions—without losing your development freedom.</em>
</p>

<p align="center">
  <a href="https://pypi.org/project/fastapi-zcore-framework/">
    <img src="https://img.shields.io/pypi/v/fastapi-zcore-framework?label=PyPI&color=teal" alt="PyPI">
  </a>
  <a href="https://github.com/fastapi-zcore-framework/zcore/blob/master/LICENSE">
    <img src="https://img.shields.io/github/license/fastapi-zcore-framework/zcore?color=purple" alt="License">
  </a>
  <a href="https://github.com/fastapi-zcore-framework/zcore/actions">
    <img src="https://img.shields.io/github/actions/workflow/status/fastapi-zcore-framework/zcore/publish.yml?label=CI&color=teal" alt="CI">
  </a>
  <a href="https://fastapi-zcore-framework.github.io/zcore">
    <img src="https://img.shields.io/badge/docs-online-purple" alt="Documentation">
  </a>
  <a href="https://pypi.org/project/fastapi-zcore-framework/">
    <img src="https://img.shields.io/pypi/pyversions/fastapi-zcore-framework?color=teal" alt="Python Versions">
  </a>
</p>

---

## What is ZCore?

**ZCore is not a framework that hides FastAPI — it is the chassis that stabilizes it.**

While FastAPI gives you a high-performance engine for HTTP, it provides no blueprint for structuring medium-to-large applications. ZCore fills that gap with:

- **🔐 Context-aware data masking** — Write one schema; sensitive fields are pruned automatically per-user.
- **🔗 Atomic Unit of Work** — Group operations into all-or-nothing transactions with delayed event dispatch.
- **⚡ Scoped Dependency Injection** — Singleton, transient, and request-scoped dependencies resolved automatically.
- **🏗️ Modular Plugin System** — Organize domains into isolated plugins with topological startup ordering.
- **🔍 Secure Dynamic Search Engine** — Nested JSON filters, cursor/offset pagination, and column-level security — zero boilerplate.
- **📦 CLI Scaffolding** — From `pip install` to running CRUD endpoints in under two minutes.

---

## Why ZCore?

| Concern | Raw FastAPI | With ZCore |
|---------|-------------|------------|
| **Endpoint Scaffolding** | Manually write 7+ files per domain | One `BaseRouter` class → 7 secure endpoints |
| **Data Leakage** | Multiple Pydantic models per role; manual conditionals | `Zchema` auto-prunes restricted fields per-user |
| **Database Transactions** | Scattered `commit()` / `rollback()` calls | `UnitOfWork` guarantees atomicity + deferred events |
| **Dependency Wiring** | Deeply nested `Depends()` chains | Constructor injection with `Inject()` — auto-resolved |
| **Search & Pagination** | Hand-written SQL per endpoint | Declarative JSON filters + cursor/offset pagination |
| **Project Layout** | No standard; every team reinvents the wheel | `zc init` + `zc startapp` — consistent domain modules |
| **Startup Orchestration** | Manual `@app.on_event` spaghetti | `Plugin` with dependency graph → topological sorting |

---

## ⚡ Quick Start

### 1. Install

```bash
pip install fastapi-zcore-framework[all]
```

### 2. Scaffold

```bash
zc init my_app && cd my_app
zc startapp tasks --template
```

### 3. Define

Open `app/tasks/models.py`:

```python
from zcore import Base
from sqlalchemy.orm import Mapped, mapped_column

class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    is_completed: Mapped[bool] = mapped_column(default=False)
```

### 4. Serve

```bash
zc run
```

Your API is live at **`http://127.0.0.1:8000`** with 7 CRUD + search endpoints ready.

> 📖 **Full walkthrough:** [10-Minute Quickstart](https://fastapi-zcore-framework.github.io/zcore/learn/quickstart/)

---

## 🏛️ Core Pillars

<details>
<summary><strong>🔐 Context Shielding (Zchema)</strong></summary>
<br>

Write a single schema. ZCore dynamically prunes input fields (preventing mass assignment) and output fields (preventing data leakage) based on the active user's permission scopes.

```python
from zcore import Zchema

class TaskCreate(Zchema):
    __model__ = "tasks"
    title: str
    assignee_email: str | None = None  # Auto-hidden from unauthorized users
```

When a user lacks `tasks:view_sensitive`, the `assignee_email` field vanishes from both validation and serialization — no `if` statements.
</details>

<details>
<summary><strong>🔗 Atomic Transactions (Unit of Work)</strong></summary>
<br>

Group multiple repository operations into a single atomic unit. Events are queued and dispatched only after a successful commit. If any operation fails, the entire transaction rolls back.

```python
from zcore import UnitOfWork

async with UnitOfWork(session, dispatcher) as uow:
    await order_repo.create(order_data)
    await inventory_repo.decrement_stock(product_id, quantity)
    
    # Queue event for post-commit dispatch safely
    uow.register_event("order.placed", {"id": order_data.id})
```
</details>

<details>
<summary><strong>⚡ Scoped Dependency Injection</strong></summary>
<br>

Inject services, repositories, and infrastructure dependencies via constructor injection. ZCore's container resolves them automatically per-request and clears request-scoped instances after each response.

```python
from zcore import BaseService, Inject

class TaskService(BaseService):
    def __init__(self, repo: TaskRepository = Inject(TaskRepository)):
        super().__init__(model=Task, repository=repo)
```
</details>

<details>
<summary><strong>🏗️ Modular Plugin System</strong></summary>
<br>

Each domain is a self-contained `Plugin` with its own models, services, routers, and lifecycle hooks. The Kernel uses topological sorting to guarantee correct startup/shutdown order.

```python
from zcore import Plugin
from .routers import router_instance

class TaskPlugin(Plugin):
    name = "tasks"
    dependencies = ["auth"]

    def setup(self, app):
        app.include_router(router_instance.router)

    async def on_startup(self):
        await cache.warm()
```
</details>

<details>
<summary><strong>🔍 Secure Search Engine</strong></summary>
<br>

A dynamic query builder that translates nested JSON filters into safe SQL — with depth-limit protection against DoS attacks.

```json
{
  "filters": [
    { "field": "priority", "op": "eq", "value": "high" },
    { "field": "is_completed", "op": "eq", "value": false }
  ],
  "sort_by": "created_at",
  "sort_order": "desc",
  "page": 1,
  "size": 20
}
```
</details>

<details>
<summary><strong>📦 CLI Scaffolding</strong></summary>
<br>

Stop copying boilerplate. The `zc` CLI generates consistent, production-ready domain modules with a single command.

| Command | Purpose |
|---------|---------|
| `zc init <name>` | Create a new project with settings, `.env`, and `main.py` |
| `zc startapp <name>` | Scaffold a domain module |
| `zc startapp <name> --template` | Scaffold with full CRUD boilerplate |
| `zc run` | Launch Uvicorn with environment-aware config |
| `zc gensecret` | Generate a cryptographically secure `SECRET_KEY` |
</details>

---

## 📖 Documentation

| Resource | Description |
|----------|-------------|
| [🚀 10-Minute Quickstart](https://fastapi-zcore-framework.github.io/zcore/learn/quickstart/) | Build a complete Task Manager API from scratch |
| [📚 Tutorial (Step-by-Step)](https://fastapi-zcore-framework.github.io/zcore/learn/overview/) | Deep dive into each architectural layer |
| [🔧 How-To Guides](https://fastapi-zcore-framework.github.io/zcore/how-to/auth-setup/) | JWT auth, transactions, field masking, storage, WebSockets |
| [🏛️ Architecture & Reference](https://fastapi-zcore-framework.github.io/zcore/features/infrastructure/di/) | Full API docs for DI, Kernel, Security, Caching, and more |
| [📄 Cheat Sheet](https://fastapi-zcore-framework.github.io/zcore/cheatsheet/) | Pocket reference for quick syntax lookup |

---

## 🤝 Contributing

Contributions are welcome! Please read our guidelines before submitting a PR.

- **Issues:** Bug reports and feature requests via [GitHub Issues](https://github.com/fastapi-zcore-framework/zcore/issues)
- **PRs:** Open a pull request with a clear description of the change
- **Local Setup:** `pip install -e ".[all,dev]"` and run `pytest` to verify

---

## 📄 License

ZCore is licensed under the **Apache License 2.0**.  
See [LICENSE](https://github.com/fastapi-zcore-framework/zcore/blob/master/LICENSE) for details.

---

<p align="center">
  <sub>Built with ☕ and architectural rigor by <a href="https://github.com/alialfostovar">Ali Alf Ostovar</a>.</sub>
</p>