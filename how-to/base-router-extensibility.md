# Project-Wide Router Extensibility

Scale your API architecture by extending the BaseRouter to enforce project-wide security standards and custom endpoint behaviors.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>Routing Architecture</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Status</span><br>
    <strong>Recommended for Scale</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Underlying Tech</span><br>
    <strong>FastAPI / Python OOP</strong>
  </div>
</div>

## The Challenge
In a rapidly growing project, standard CRUD routers often become a source of technical debt. You might find yourself manually adding the same "Admin Only" dependency to the `DELETE` route of 20 different modules. Or perhaps you decide that every `GET_ALL` request across the entire project must include a specific rate-limiting header. 

Using raw FastAPI `APIRouter` or rigid scaffolding tools forces you to repeat this logic in every file. If the requirement changes, you have to find and replace code in dozens of places, increasing the risk of security oversights.

## The ZCore Elegance
ZCore's `BaseRouter` is designed for **Object-Oriented Inheritance**. Instead of using it directly, you can create a `ProjectBaseRouter` for your API. By overriding the lifecycle methods—specifically `get_route_dependencies` and `get_route_action`—you can inject global security policies or modify the naming convention of permissions across all your domain modules from a single source of truth.

=== "ZCore Architectural Extension"
        :::python
        # 1. Define your project-wide base router
        class MyProjectBaseRouter(BaseRouter[CreateSchemaType, UpdateSchemaType]):
            
            def get_route_dependencies(self, route_key: RouteKey, action: str):
                # Enforce project-wide policy: All DELETEs require 'superadmin'
                deps = super().get_route_dependencies(route_key, action)
                
                if route_key == RouteKey.DELETE:
                    deps.append(HasScopes("superadmin"))
                    
                return deps

        # 2. Use your custom base in domain routers
        class UserRouter(MyProjectBaseRouter[UserCreate, UserUpdate]):
            model = User
            # DELETE /users now automatically requires 'users:delete' AND 'superadmin'

=== "FastAPI Manual Repetition"
        :::python
        # You must remember to add the dependency to every router manually
        router = APIRouter(prefix="/users")

        @router.delete("/{id}", dependencies=[Depends(HasScopes("users:delete")), Depends(HasScopes("superadmin"))])
        async def delete_user(id: uuid.UUID):
            pass

        # ... Then repeat this exact dependency list in /products, /orders, /billing ...
        # If the policy changes to "manager" instead of "superadmin", you edit 20 files.

---

## Boundaries & Integration
Customized routers maintain full compatibility with the FastAPI ecosystem.

*   **Dependency Normalization:** ZCore's internal `_normalize_dependencies` helper ensures that whether you return a raw callable, a class, or a `FastAPI.Depends` object from your overrides, it is correctly wrapped and registered [web/base_router.py].
*   **Selective Overrides:** You can override a single endpoint method (e.g., `delete_endpoint`) in your project-base to implement "Soft Delete" logic project-wide, while leaving `POST` and `GET` to use the standard ZCore implementation.
*   **Middleware Alternatives:** For logic that applies to *all* requests regardless of the route (like Correlation IDs), use ZCore Middlewares. Use Router Extensions for logic that varies by `RouteKey` or `Model`.

---

## Under-the-Hood Spec

### 1. The RouteKey Enum
The `RouteKey` is a `StrEnum` that maps directly to the scaffolded operations: `POST`, `GET`, `GET_ALL`, `SEARCH`, `UPDATE`, `PATCH`, and `DELETE` [web/base_router.py]. This allows your overrides to use clean, type-safe logic when determining which dependencies to inject.

### 2. Automatic Dependency Injection (DI)
The `BaseRouter` doesn't just register functions; it registers closures that utilize `Inject(self.service)` [web/base_router.py]. This means that even in your project-wide base router, the correct domain-specific service is always resolved from the IoC container at runtime.

### 3. Scoped Action Derivation
The `get_route_action` method bridges the router to the model [web/base_router.py]. By default, it calls `self.model.actions().VIEW` or `CREATE`. If your project uses a different naming convention for permissions (e.g., `view_products` instead of `products:view`), you can override this single method in your `ProjectBaseRouter` to re-map actions project-wide.

!!! info "Advanced Dependency Logic"
    The `get_route_dependencies` method is called during the router's `__init__` phase [web/base_router.py]. This means your dependency tree is pre-compiled at startup, maintaining FastAPI's high performance during the request-response cycle.