# API Routing Mechanics

Intercept HTTP traffic with a custom route handler that preserves response classes, injects Vary headers on context-pruned payloads, and exposes dynamic JSON-Schema introspection.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>Routing Infrastructure</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Status</span><br>
    <strong>Security Integration</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Underlying Tech</span><br>
    <strong>FastAPI APIRoute / Pydantic</strong>
  </div>
</div>

## The Challenge

Standard FastAPI routes are stateless with respect to security context. As a result, developers often encounter:

1.  **Response Class Overwriting:** Middleware or custom response classes are silently replaced by `JSONResponse`, breaking specialized serialization logic.
2.  **Cache Invisibility:** When the response payload is dynamically pruned based on user permissions, intermediate CDNs or proxies may cache a pruned response and serve it to a privileged user, leaking restricted data.
3.  **Schema Blindness:** Frontend teams have no standardized way to introspect the current schema—especially which fields are restricted for the active user—without manual API documentation or hard-coded logic.

## The ZCore Elegance

`ZCoreAPIRoute` is a drop-in replacement for FastAPI's `APIRoute`. It intercepts every request, conditionally generates context-aware JSON-Schema responses when `?schema=true` is appended, and appends `Vary: Authorization, Cookie` headers to any response that has been security-pruned.

=== "ZCore Transparent Routing"
        :::python
        from zcore.web.api_router import ZCoreAPIRoute
        from fastapi import APIRouter

        router = APIRouter(route_class=ZCoreAPIRoute)

        @router.post("/products", openapi_extra={"expose_schema": True})
        async def create(data: ProductCreate, service: ProductService = Inject(ProductService)):
            return await service.create(data)
        
        # GET /products?schema=true  →  Returns JSON-Schema with restricted fields pruned
        # POST /products              →  Response includes Vary: Authorization, Cookie if pruning occurred

=== "Standard FastAPI Routing"
        :::python
        from fastapi import APIRouter

        router = APIRouter()

        @router.post("/products")
        async def create(data: ProductCreate, service: ProductService = Depends(get_service)):
            # No schema introspection
            # No Vary header management
            # Plain JSONResponse always used
            return await service.create(data)

---

## Execution Flow

<p align="center">
  <img src="https://raw.githubusercontent.com/fastapi-zcore-framework/zcore/master/docs/assets/api-router.png" 
  alt="Execution Flow" width="700">
</p>

---

## Boundaries & Integration

ZCoreAPIRoute works transparently with the rest of the ZCore ecosystem.

*   **BaseRouter Compatible:** The `BaseRouter` class in `web/base_router.py` uses `ZCoreAPIRoute` as its default `route_class`. Any scaffolded endpoint automatically inherits schema exposure and Vary header management.
*   **Response Class Preservation:** When initializing, `ZCoreAPIRoute` inspects the current `response_class`. If it is the default `JSONResponse`, it swaps in `ZCoreJSONResponse` (which uses ZCore's unified JSON encoder). Custom response classes are left untouched.
*   **Manual Endpoints:** Functional endpoints registered on a standard `APIRouter` are unaffected. Only routes using `ZCoreAPIRoute` (or a `BaseRouter` subclass) participate in the security-aware lifecycle.

---

## Under-the-Hood Spec

### 1. Response Class Preservation Logic

Inside `ZCoreAPIRoute.__init__`, the constructor checks the inherited `response_class` [web/api_router.py]. If the class resolves to the standard FastAPI `JSONResponse`, it is replaced with `ZCoreJSONResponse`. Any custom subclass (e.g., `ORJSONResponse`) is preserved, ensuring third-party serializers are never silently overridden.

### 2. Vary Header Append on Context-Pruned Responses

After the route handler completes, `custom_route_handler` inspects `get_restricted_fields()` [web/api_router.py]. If the set is non-empty and the response is JSON, the method appends `Authorization` and `Cookie` to the existing `Vary` header. Duplicates are eliminated by lower-casing existing values, preventing header bloat on repeated requests.

### 3. Schema Extraction via Dependency Introspection

`find_input_schema` iterates over `dependant.body_params` to locate the body Pydantic model [web/api_router.py]. `find_output_schema` recursively unpacks generic origin types (e.g., `ResponseWrapper[ProductOut]`) to extract the inner model. This allows `ZCoreAPIRoute` to resolve the effective schema even when wrapped in generic containers.

### 4. Request Body Caching

`ZCoreRequest` overrides `body()` to cache the byte stream on first read [web/api_router.py]. This prevents downstream middlewares or validators from consuming the stream and leaving subsequent readers with an empty payload.

!!! info "Schema Exposure Restriction"
    Schema introspection (`?schema=true`) is only enabled on routes with `openapi_extra={"expose_schema": True}`. This prevents accidental leakage of internal model structures on endpoints that do not opt in.