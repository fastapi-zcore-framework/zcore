# Zchema Security & Schema Pruning

Unify input validation, response serialization, and dynamic JSON-Schema generation into a single domain-aware base class that silently enforces data-masking policies.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>Schema Security Layer</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Status</span><br>
    <strong>Security Core</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Underlying Tech</span><br>
    <strong>Pydantic V2 / contextvars</strong>
  </div>
</div>

## The Challenge

In a typical FastAPI application, security schema management suffers from three distinct failure modes:

1.  **Schema Fragmentation:** To prevent data leakage, developers define multiple Pydantic models per entity (e.g., `ProductCreate`, `ProductOutPublic`, `ProductOutAdmin`, `ProductUpdate`). A single new restricted field must be added to every variant, leading to copy-paste errors.
2.  **Mass Assignment Vulnerabilities:** Input schemas that accept all model fields allow a malicious user to send unexpected fields (e.g., `is_admin=true`) that get written directly to the database.
3.  **Context-Blind Serialization:** Response serialization is static. A service returns the same fields regardless of who is making the request, forcing every endpoint to manually check permissions before building the response.

## The ZCore Elegance

`Zchema` is a drop-in replacement for `pydantic.BaseModel` that is domain-aware and context-sensitive. You define a single schema per entity, annotate it with `__model__` to declare its database domain, and Zchema automatically prunes restricted fields during validation, serialization, and JSON-Schema generation—all based on the active thread-safe context.

=== "ZCore Unified Zchema"
        :::python
        from zcore.web.projection import Zchema

        class ProductBase(Zchema):
            __model__ = "products"          # Domain binding
            name: str
            price: float
            secret_cost: float | None = None  # Restricted when context says so

        # Inside a request where "products.secret_cost" is restricted:
        schema = ProductBase(name="X", price=10, secret_cost=100)
        # schema.model_dump() → {"name": "X", "price": 10}  (secret_cost pruned)

        # GET /products?schema=true returns JSON-Schema WITHOUT secret_cost

=== "Standard Pydantic Multi-Model"
        :::python
        from pydantic import BaseModel

        class ProductCreate(BaseModel):
            name: str
            price: float
            secret_cost: float | None = None

        class ProductOut(BaseModel):
            name: str
            price: float
            # secret_cost is missing—but so is any admin-only field

        # Must maintain N models per entity
        # Each new field requires updates across ALL variants
        # No automatic context-driven pruning

---

## The Pruning Pipeline

<p align="center">
  <img src="https://raw.githubusercontent.com/fastapi-zcore-framework/zcore/master/docs/assets/zchema.png" 
  alt="The Pruning Pipeline" width="700">
</p>

---

## Boundaries & Integration

Zchema is the backbone of ZCore's data-masking strategy and integrates seamlessly with the broader ecosystem.

*   **ResponseWrapper Inheritance:** `ResponseWrapper` inherits from `Zchema`, meaning all API responses automatically benefit from context-driven serialization pruning.
*   **BaseRouter Schema Resolution:** The `BaseRouter` uses `create_schema`, `update_schema`, and `schema_out`—all expected to be `Zchema` subclasses. The router's `ZCoreAPIRoute` invokes `model_json_schema()` on these classes, which triggers the customized schema generation path.
*   **Context Decoupling:** Zchema never directly inspects HTTP headers or tokens. It reads restricted field paths from the thread-safe context (`get_restricted_fields()`), which is populated by upstream middleware or authentication logic.

---

## Under-the-Hood Spec

### 1. Domain Mapping via `__model__`

Each Zchema subclass declares a `__model__` class variable matching its database table or domain name (e.g., `"products"`) [web/projection.py]. When the context holds a restricted path like `"products.secret_cost"`, `_get_relative_restricted_paths` strips the domain prefix and returns `{"secret_cost"}`. A wildcard path `"products"` maps to `{"*"}`, which clears the entire payload.

### 2. Input Pruning via `model_validator(mode="before")`

The `filter_restricted_inputs` validator executes before any Pydantic field validation [web/projection.py]. It makes a shallow copy of the input dictionary and calls `_prune_data` to remove any keys whose dotted paths match the restricted set. This prevents mass assignment attacks where a user injects privileged fields into a create or update payload.

### 3. Output Pruning via `model_serializer(mode="wrap")`

The `secure_serializer` wraps the default serialization handler [web/projection.py]. After Pydantic produces the standard dictionary, the method applies the same pruning logic to strip restricted fields from the serialized output before returning the response.

### 4. Schema Pruning via `__get_pydantic_json_schema__`

Zchema overrides Pydantic V2's JSON-Schema generation hook [web/projection.py]. It calls the standard handler to produce the full schema, then recursively walks the `properties` and `required` lists to remove any fields that are restricted for the current context. This ensures that frontend forms generated from `?schema=true` never include fields the user cannot see or edit.

### 5. Recursive Nested Pruning

The `_prune_data` helper handles nested structures [web/projection.py]. For a restriction like `"orders.items.price"`, it descends into `data["orders"]["items"]` and prunes the `price` key from each dictionary or list element. This enables field-level masking across complex, deeply nested Pydantic models.

!!! info "Performance Note"
    Zchema restricts input and output fields by value-copying the data dictionary before pruning. This ensures the original model instance is never mutated, preserving data integrity for downstream operations that may bypass the serializer.

!!! danger "Security Note"
    Because pruning happens at the Pydantic layer, it applies universally—including in background tasks, CLI commands, or any code path that uses `model_dump()` on a Zchema instance while a restricted context is active. Always reset the context when spawning isolated work.