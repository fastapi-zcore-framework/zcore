# 🧱 How-To: Project-Wide Base Router & Dependency Scalability

## ❓ The Problem

In a real-world ZCore project, you often need to apply **global middleware-like behavior** across all your API routes — for example:

*   📝 Logging the request's IP address and user agent
*   ⏱️ Rate-limiting or throttling
*   🔍 Enforcing tenant isolation checks
*   📊 Collecting observability metrics (request duration, status codes)

Without a centralized mechanism, you would have to duplicate these dependencies in **every single router** — violating the DRY principle and making maintenance a nightmare.

---

## 🛠️ The ZCore Solution

ZCore's `get_route_dependencies` method makes it trivial to build a **project-wide base router** that automatically injects shared dependencies into every endpoint. This follows the same proven pattern used by Django's class-based views, Spring's `ApiController`, and .NET's controller base classes.

### 🏗️ Step 1: Create a Project-Wide Base Router

Create a single file — for example `app/core/router.py` — that contains your application's foundational router class:

```python
# app/core/router.py
from zcore import BaseRouter, RouteKey
from typing import Any

class AppBaseRouter(BaseRouter[CreateSchemaType, UpdateSchemaType]):
    """Foundation router for the entire application.

    Every domain router should inherit from this class to receive
    project-wide dependencies automatically.
    """

    def get_route_dependencies(self, route_key: RouteKey, action: str) -> list[Any]:
        # 1. Inject project-wide dependencies (monitoring, logging, rate-limiting)
        dependencies = [LogRequestIP(), RateLimiter()]

        # 2. Delegate to ZCore's default behavior (HasScopes, etc.)
        dependencies.extend(super().get_route_dependencies(route_key, action))

        return dependencies
```

### 🎯 Step 2: Domain Routers Inherit from Your Base

Once the base router is defined, every domain router becomes dramatically simpler:

```python
# app/products/routers.py
from app.core.router import AppBaseRouter

class ProductRouter(AppBaseRouter):
    model = Product
    # That's it! Monitoring, IP logging, and security scopes are all handled automatically.
```

---

## 💎 Why This Pattern Is a Scalability Masterpiece

### 1. 🧩 DDD-Friendly: Different Bases for Different Contexts

In large projects, you may need different behavior for different domain contexts. You can create **multiple base routers** tailored to specific needs:

```python
# Base for admin endpoints (strict auditing, admin role check)
class AdminBaseRouter(BaseRouter[CreateSchemaType, UpdateSchemaType]):
    def get_route_dependencies(self, route_key: RouteKey, action: str) -> list[Any]:
        dependencies = [AuditLogger(), RequireAdminRole()]
        dependencies.extend(super().get_route_dependencies(route_key, action))
        return dependencies

# Base for public endpoints (lighter monitoring)
class PublicBaseRouter(BaseRouter[CreateSchemaType, UpdateSchemaType]):
    def get_route_dependencies(self, route_key: RouteKey, action: str) -> list[Any]:
        dependencies = [RateLimiter()]
        dependencies.extend(super().get_route_dependencies(route_key, action))
        return dependencies
```

This level of granularity was **impossible** with the old static permission properties.

### 2. 📐 Pure DRY & KISS

*   **DRY:** Global logic is written **once** in the base router file. Zero duplication across domains.
*   **KISS:** Domain developers don't need to think about infrastructure concerns. They just inherit and declare their model.

### 3. 🚀 Superior Developer Experience (DX)

This pattern is exactly what senior architects use in enterprise frameworks:

| Framework | Pattern |
| :--- | :--- |
| **Django** | Class-based views with `BaseView` |
| **Spring Boot** | `@ControllerAdvice` / Base `ApiController` |
| **ASP.NET Core** | Base `ControllerBase` class |
| **ZCore** | `get_route_dependencies` in project base router |

---

## 🔧 Selective Override Within a Domain

Even with a project-wide base, individual domains can still override specific dependencies without losing the global behavior:

```python
# app/orders/routers.py
from app.core.router import AppBaseRouter
from zcore.web.base_router import RouteKey

class OrderRouter(AppBaseRouter):
    model = Order

    def get_route_dependencies(self, route_key: RouteKey, action: str) -> list[Any]:
        # Add a domain-specific check for DELETE operations
        if route_key == RouteKey.DELETE:
            return [CanCancelOrder()]

        # Everything else inherits global deps + scopes via super()
        return super().get_route_dependencies(route_key, action)
```

---

## 🧪 Verification

With the `AppBaseRouter` in place, every endpoint across every domain will:

1. 📝 Log the requesting IP address (`LogRequestIP`)
2. ⏱️ Apply rate-limiting (`RateLimiter`)
3. 🛡️ Enforce the appropriate security scope (`HasScopes`)
4. 🎯 Execute the domain-specific business logic

All of this happens **deterministically at startup** — zero runtime reflection, zero magic.

---

## 💡 Engineering Insights

!!! tip "💡 One Method to Rule Them All"
    The old architecture required maintaining up to 8 separate static class variables (`POST_PERMISSIONS`, `GET_PERMISSIONS`, etc.) across every router. The new architecture reduces this to a **single method override** — or zero overrides if you just need defaults.

!!! info "🛡️ Composition Over Inheritance"
    While inheritance is powerful, you can also compose dependencies by creating reusable dependency factories that your base router calls. This keeps the base router itself clean and focused.

!!! warning "⚠️ Order Matters"
    Dependencies in the list are executed in the order they are defined. If you need authentication to run before rate-limiting, place `HasScopes` (or your auth dependency) **before** the rate limiter in the returned list.