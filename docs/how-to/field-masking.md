# Dynamic Role-Based Field Masking

Automatically prune sensitive data from inputs and outputs based on granular, context-aware security policies.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>Context Shielding</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Status</span><br>
    <strong>Recommended Core</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Underlying Tech</span><br>
    <strong>Pydantic V2 / contextvars</strong>
  </div>
</div>

## The Challenge
Modern APIs often deal with "Multifaceted Data"—where the same record (e.g., a **User Profile**) has different visible fields depending on who is asking.
1.  **The Public** should only see `username` and `avatar`.
2.  **The Owner** should also see `email` and `billing_address`.
3.  **The Admin** should see everything, including `internal_notes` and `risk_score`.

In standard FastAPI, this usually forces developers to create a separate Pydantic model for every role (`UserPublic`, `UserPrivate`, `UserAdmin`) and write complex `if/else` logic in routers to choose the correct model. This is error-prone and causes "Schema Explosion."

## The ZCore Elegance
ZCore's `Zchema` allows you to define **one model** for all roles. By setting the `__model__` attribute, the schema becomes "context-aware." When the request starts, your security middleware populates a list of `restricted_fields` (e.g., `["users.internal_notes"]`). ZCore then automatically strips these fields from incoming JSON payloads (Mass Assignment protection) and outgoing JSON responses (Leakage protection).

=== "ZCore Context Masking"
        :::python
        from zcore import Zchema, request_context

        class UserSchema(Zchema):
            __model__ = "users" # Ties to the 'users' domain
            
            username: str
            email: str
            internal_notes: str | None = None

        # Inside a middleware or dependency:
        restricted = ["users.internal_notes"]
        if not user.is_admin:
            with request_context(user_id=user.id, fields=restricted):
                # Outgoing response now automatically 
                # masks 'internal_notes'
                return UserSchema.model_validate(user_record)

=== "FastAPI Manual Projection"
        ::python
        # Multiple models required
        class UserPublic(BaseModel):
            username: str

        class UserPrivate(UserPublic):
            email: str
            internal_notes: str

        @router.get("/users/{id}")
        async def get_user(id: uuid.UUID, user: User = Depends(get_user)):
            record = await db.get(id)
            # Manual role-based branching logic
            if user.is_admin:
                return UserPrivate.model_validate(record)
            return UserPublic.model_validate(record)

---

## Boundaries & Integration
ZCore's masking logic is a non-destructive layer built on top of Pydantic.

*   **Pydantic Native:** Pruning happens during Pydantic's internal `model_validator` and `model_serializer` phases [web/projection.py]. Your logic inside the service or repository layers remains untouched—you always work with full objects.
*   **Opt-In Masking:** If a schema does not define `__model__`, ZCore ignores it. It behaves like a standard `BaseModel`.
*   **Freedom to Bypass:** If you need to force-send a restricted field for a specific edge case, you can use a standard `pydantic.BaseModel` for that specific route, which will bypass ZCore's context-aware pruning.

---

## Under-the-Hood Spec

### 1. The Recursive `_prune_data` Logic
ZCore doesn't just check top-level keys. The internal `_prune_data` method recursively traverses nested dictionaries and lists [web/projection.py]. If you restrict `orders.items.cost`, ZCore will find every `cost` field inside the `items` list of an `Order` object and remove it, regardless of the nesting depth.

### 2. Dynamic JSON-Schema Pruning
When `expose_schemas` is enabled on a router, ZCore overrides `__get_pydantic_json_schema__` [web/projection.py]. It doesn't just mask the data; it **masks the documentation**. If a user lacks permission to see `internal_notes`, that field will not appear in the JSON-Schema returned by `?schema=true`, allowing your frontend to dynamically hide form inputs.

### 3. Cache-Safe `Vary` Headers
Because the same URL can return different JSON content based on the user's permissions, ZCore's `ZCoreAPIRoute` automatically appends `Authorization` or `Cookie` to the `Vary` HTTP header [web/api_router.py]. This ensures that downstream CDNs or browser caches do not accidentally serve a cached "Admin" response to a "Public" user.

!!! info "Security Policy"
    Restricted fields are defined as dot-paths (e.g., `model_name.field_name`). To restrict an entire model, you can use the model name itself (e.g., `users`). This will cause the entire schema to return an empty object if the user is unauthorized.