# JWT Authentication & Scopes

Secure your API with Argon2id hashing, flexible JWT signing, and protocol-based authorization guards.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>Security / Protocol</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Status</span><br>
    <strong>Core Core</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Underlying Tech</span><br>
    <strong>Argon2id / PyJWT / contextvars</strong>
  </div>
</div>

## The Challenge
Implementing security in FastAPI often leads to "Hardcoded Identity" problems. Developers either tightly couple their routes to a specific SQLAlchemy User model or manually parse JWTs in every dependency. Furthermore, many projects still use aging hashing algorithms like BCrypt or, worse, run production environments with default, insecure secret keys found in git history.

## The ZCore Elegance
ZCore introduces **Protocol-Based Security**. Instead of depending on a concrete model, the security layer depends on a `UserProtocol`. This allows you to use any database (SQL, NoSQL, or External Auth) as long as your user object provides the required attributes. Security is enforced through reusable `BasePermission` classes that integrate seamlessly with `BaseRouter` and the kernel's context.

=== "ZCore Permission Guards"
        :::python
        from zcore import BaseRouter, RouteKey
        from zcore.security import HasScopes

        class DocumentRouter(BaseRouter[DocCreate, DocUpdate]):
            model = Document
            # ... standard config ...

            def get_route_dependencies(self, route_key: RouteKey, action: str):
                # Automated scope checks based on model actions
                # e.g., "documents:delete"
                if route_key == RouteKey.DELETE:
                    return [HasScopes("admin", action)]
                
                return super().get_route_dependencies(route_key, action)

=== "FastAPI Manual Auth"
        :::python
        # Manual verification in every route
        @router.delete("/{id}")
        async def delete_doc(
            id: uuid.UUID, 
            user: User = Depends(get_current_user)
        ):
            # 1. Manual active check
            if not user.is_active: raise AuthError()
            
            # 2. Manual scope string management
            if "admin" not in user.scopes and "documents:delete" not in user.scopes:
                raise ForbiddenError()
                
            # 3. Manual service call
            await service.delete(id)

---

## Implementation Guide

### 1. Define your User Model
Ensure your SQLAlchemy or Pydantic user model implements the `UserProtocol`.

```python
class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_superuser: Mapped[bool] = mapped_column(default=False)
    
    @property
    def all_scopes(self) -> set[str]:
        # Return a set of strings representing user permissions
        return {r.name for r in self.roles}
```

### 2. Override the Identity Provider
In your `main.py`, you must tell ZCore how to resolve the current user. ZCore provides a `get_current_user_stub` that you must override.

```python
from zcore.security import get_current_user_stub, decode_token

async def my_auth_provider(token: str = Depends(oauth2_scheme)) -> User:
    payload = decode_token(token)
    user_id = payload.get("sub")
    # Fetch user from DB
    return await user_service.get(user_id)

# Register the override
app.dependency_overrides[get_current_user_stub] = my_auth_provider
```

---

## The Auth Lifecycle

<p align="center">
  <img src="https://raw.githubusercontent.com/fastapi-zcore-framework/zcore/master/docs/assets/auth-setup.png" 
  alt="The Auth Lifecycle" width="700">
</p>


---

## Boundaries & Integration
ZCore provides the cryptographic and logic chassis, while you provide the data.

*   **OAuth2 Compatible:** ZCore's JWT utilities work perfectly with FastAPI's `OAuth2PasswordBearer`.
*   **Hashing Freedom:** While ZCore provides `get_password_hash` using Argon2id, you can use any library for hashing; ZCore services and repositories accept raw strings.
*   **Bypass Identity:** If you have public routes, simply don't add the `HasScopes` dependency. The `request_context` will remain empty (user_id = None), and ZCore's masking logic will treat the request as unauthenticated.

---

## Under-the-Hood Spec

### 1. Fatal Security Violation Guard
The `jwt.py` module contains a hard-coded check [security/jwt.py]. If the `ENVIRONMENT` is set to `production` and the `SECRET_KEY` matches the framework's default fallback string, the application will **abort startup** with a `RuntimeError`. This prevents the most common source of production JWT vulnerabilities.

### 2. Argon2id Hardening
ZCore defaults to Argon2id (the winner of the Password Hashing Competition). The `hashing.py` module configures high-entropy parameters by default: 64MB memory cost and 3 iterations [security/hashing.py]. These parameters can be tuned via `ZCoreCoreSettings` to balance security and latency.

### 3. Protocol-Based "Duck Typing"
The `HasScopes` permission does not perform an `isinstance()` check against a database model [security/permissions.py]. Instead, it relies on the `UserProtocol` interface. This means your "User" could be a database record, a cached Redis object, or even a Mock object during testing, as long as it has `id`, `is_active`, and `all_scopes`.

!!! success "Security Note"
    By utilizing the `user_context` within your identity provider, the authenticated user's ID is available project-wide via `get_current_user_id()` without passing the user object through every function call.