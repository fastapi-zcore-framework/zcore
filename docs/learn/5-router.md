# Progressive API Scaffolding

Generate 7 secure CRUD and search endpoints in seconds with zero manual boilerplate.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>Web Router Scaffolding</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Status</span><br>
    <strong>Optional Utility</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Underlying Tech</span><br>
    <strong>FastAPI / Starlette</strong>
  </div>
</div>

## The Challenge
Writing standard CRUD (Create, Read, Update, Delete) routes in FastAPI is repetitive. For every new domain, developers must:
1. Define 5-7 path functions.
2. Manually inject the correct service.
3. Apply standard status codes (`201 Created` vs `200 OK`).
4. Wrap every response in a consistent envelope.
5. Manually apply security dependencies (scopes) that often fall out of sync with the database model permissions.

## The ZCore Elegance
The `BaseRouter` automates the scaffolding of a fully secure API. It maps the standard HTTP methods to your business service and automatically derives security scopes from your model's `.actions()`. It supports dynamic sorting, filtering (via the Search engine), and pagination out of the box.

=== "ZCore Scaffolding"
        :::python
        from zcore import BaseRouter, RouteKey
        from .schemas import ProductCreate, ProductUpdate, ProductResponse
        from .services import ProductService
        from .models import Product

        class ProductRouter(BaseRouter[ProductCreate, ProductUpdate]):
            model = Product
            create_schema = ProductCreate
            update_schema = ProductUpdate
            schema_out = ProductResponse
            service = ProductService
            
            prefix = "/products"
            tags = ["Products"]
            expose_schemas = True # Enables ?schema=true

=== "FastAPI Raw Scaffolding"
        :::python
        # To achieve the same result, you must write ~80 lines of code:
        router = APIRouter(prefix="/products", tags=["Products"])

        @router.post("/", status_code=201, response_model=ResponseWrapper[ProductResponse])
        async def create(data: ProductCreate, service: ProductService = Depends(get_product_service)):
            if "products:create" not in user.scopes: # Manual scope check
                raise ForbiddenError()
            result = await service.create(data)
            return ResponseWrapper(data=result)
        
        # ... Repeat for GET, GET ALL, SEARCH, PUT, PATCH, DELETE ...
        # (And don't forget to handle pagination and 404s manually)

---

## Boundaries & Integration
ZCore routers provide "Progressive Scaffolding"—they grow with your complexity without locking you in.

*   **Endpoint Exclusion:** Use the `exclude` attribute to skip scaffolding specific routes.
    `exclude = {RouteKey.DELETE, RouteKey.PATCH}`
*   **OOP Freedom:** Every scaffolded endpoint is an overridable method (e.g., `create_endpoint`). You can override them to add custom logic while keeping the rest of the router automated.
*   **Dynamic Dependencies:** Override `get_route_dependencies` to inject custom authentication, logging, or rate-limiting for specific route keys (e.g., stricter auth for `DELETE`).
*   **Standard APIRouter:** The `self.router` attribute is a standard FastAPI `APIRouter`. You can add custom, raw FastAPI endpoints to it at any time using standard decorators.

---

## Under-the-Hood Spec

### 1. Unified Response Class
ZCore routers use the `ZCoreAPIRoute` class by default [web/api_router.py]. This specialized route ensures that all responses use the `ZCoreJSONResponse`, which utilizes the framework's custom JSON encoder to safely handle UUIDs, Datetime, and Decimal types without manual conversion.

### 2. Automated Action Mapping
The router automatically coordinates with your model's `Actions` system [web/base_router.py]. It maps `RouteKey.POST` to `model.actions().CREATE` and `RouteKey.DELETE` to `model.actions().DELETE`. This ensures that your API's security requirements are always physically bound to your database schema.

### 3. Dynamic Schema Extraction
If `expose_schemas` is enabled, the router intercepts requests with the `?schema=true` query parameter [web/api_router.py]. It identifies the target Pydantic model for the current route (whether it's an input model for POST or an output model for GET), generates its JSON-Schema, and prunes it based on the user's active context restrictions before returning it.

### 4. Vary Header Management
To prevent caching issues when field masking is active, the `ZCoreAPIRoute` automatically appends `Authorization` or `Cookie` to the HTTP `Vary` header if restricted fields are detected in the active context [web/api_router.py]. This tells proxies and browsers that the response content may change based on the user's identity.