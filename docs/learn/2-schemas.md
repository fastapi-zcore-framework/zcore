# Context-Aware Data Shielding

Define one schema; ZCore handles input pruning and output masking based on active security context.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>Schema Wrapper</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Status</span><br>
    <strong>Highly Recommended</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Underlying Tech</span><br>
    <strong>Pydantic V2 / ContextVars</strong>
  </div>
</div>

## The Challenge
Modern APIs often suffer from two major data integrity issues:
1.  **Mass Assignment:** An attacker sends `{"is_admin": true}` in a registration payload, and the backend blindly persists it.
2.  **Data Leakage:** Sensitive fields (like `internal_notes` or `secret_cost`) are accidentally included in a public GET response.

To solve this in raw FastAPI, developers typically create a "Schema Explosion"—multiple Pydantic models for every single operation: `UserCreate`, `UserUpdate`, `UserPublicResponse`, `UserAdminResponse`, and `UserOwnerResponse`. This leads to massive maintenance overhead and fragile code.

## The ZCore Elegance
The `Zchema` class eliminates schema explosion. By linking a schema to its database `__model__` name, ZCore automatically cross-references the active `restricted_fields` in the current context. If a field is restricted, ZCore silently prunes it from incoming payloads and masks it in outgoing responses—all using a single model definition.

=== "ZCore Unified Zchema"
        :::python
        from zcore import Zchema

        class ProductSchema(Zchema):
            __model__ = "products" # Links to Product.__tablename__
            
            name: str
            price: float
            secret_cost: float | None = None # Restricted field

        # If "products.secret_cost" is in restricted_fields:
        # 1. POST input: 'secret_cost' is silently stripped.
        # 2. GET response: 'secret_cost' is masked from JSON output.
        # 3. ?schema=true: 'secret_cost' is removed from JSON-Schema.

=== "FastAPI Schema Explosion"
        :::python
        # You are forced to maintain 3+ models for the same entity
        class ProductBase(BaseModel):
            name: str
            price: float

        class ProductCreate(ProductBase):
            pass # No secret_cost allowed here

        class ProductResponsePublic(ProductBase):
            id: uuid.UUID

        class ProductResponseAdmin(ProductResponsePublic):
            secret_cost: float # Only for admins
            
        # In your router, you must manually select the right class:
        if user.is_admin:
            return ProductResponseAdmin.model_validate(product)
        return ProductResponsePublic.model_validate(product)

---

## Boundaries & Integration
ZCore provides security shielding without breaking the Pydantic ecosystem.

*   **Pydantic V2 Native:** `Zchema` inherits from `pydantic.BaseModel`. All Pydantic features like `Field`, `computed_field`, and `model_validator` work out of the box.
*   **Automatic Middleware Integration:** Pruning only works if the `ScopedDependencyMiddleware` and `request_context` are active. If used outside a ZCore request, it behaves exactly like a standard Pydantic model.
*   **Bypass:** If you need a schema that never prunes data regardless of context, simply inherit from `pydantic.BaseModel` instead of `Zchema`.

---

## Under-the-Hood Spec

### 1. The `model_serializer` Wrap
ZCore uses the Pydantic V2 `model_serializer(mode="wrap")` hook [projection.py]. When a response is being generated, ZCore intercepts the dictionary representation, identifies the relative paths of restricted fields for the specific `__model__`, and recursively removes them. This happens at the last possible moment before serialization, ensuring zero data leakage.

### 2. Silent Input Pruning
The `model_validator(mode="before")` hook [projection.py] acts as a guard against Mass Assignment. Before data is even validated against the model's types, ZCore prunes any keys that the active user is not allowed to touch. This prevents unauthorized fields from ever reaching your service or repository layers.

### 3. Recursive Dot-Path Resolution
Restriction paths can be specific or broad. For example, if `restricted_fields` contains `products.category.internal_id`, ZCore's internal `_prune_data` method will traverse nested dictionaries or lists within the `Product` schema to find and remove that specific deeply nested key [projection.py].

!!! info "Security Isolation"
    ZCore's pruning logic is strictly read-only regarding the original data object; it operates on a copy during serialization to ensure the internal application state remains intact while the external representation is secured.