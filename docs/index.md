<div style="display: flex; flex-direction: column; align-items: center; text-align: center; padding: 4rem 0;">
  <img src="https://raw.githubusercontent.com/fastapi-zcore-framework/zcore/master/docs/assets/banner.png" alt="ZCore Logo" style="max-width: 500px; width: 100%; margin-bottom: 2rem;">
  <p style="font-size: 1.25rem; color: #a1a1aa; max-width: 700px; line-height: 1.625; margin-bottom: 2.5rem;">
    A pragmatic and complementary architectural layer built on top of FastAPI. 
    Standardize your structure, protect your data, and manage atomic transactions—without losing your development freedom.
  </p>
  <div style="display: flex; flex-wrap: wrap; gap: 1rem; margin-bottom: 2rem; justify-content: center; align-items: center;">
    <a href="learn/installation/" style="padding: 0.875rem 2rem; border-radius: 0.375rem; background-color: #f4f4f5; color: #09090b; font-weight: bold; text-decoration: none; transition: all 0.2s; display: inline-block;">
      Get Started
    </a>
    <a href="https://github.com/fastapi-zcore-framework/zcore" style="padding: 0.875rem 2rem; border-radius: 0.375rem; border: 1px solid #27272a; color: #a1a1aa; font-weight: bold; text-decoration: none; transition: all 0.2s; display: inline-block;" target="_blank">
      GitHub Repository
    </a>
  </div>
  <div style="padding: 0.875rem 1.5rem; background-color: #18181b; border: 1px solid #27272a; border-radius: 0.375rem; font-family: monospace; font-size: 0.875rem; color: #d4d4d8;">
    pip install fastapi-zcore-framework[all]
  </div>
</div>

---

## From Chaos to Structure

FastAPI is highly performant but structureless, often leading to scattered database sessions, repetitive CRUD boilerplate, and complex dependency wiring in larger teams. 

ZCore acts as a structured chassis. See how ZCore streamlines standard web operations while keeping you fully in control:

=== "ZCore (35 Lines — 7 Secure Endpoints)"

        :::python
        from zcore import BaseRouter, BaseService, BaseRepository, Base, Zchema
        from sqlalchemy.orm import Mapped, mapped_column
        import uuid

        # 1. Define Model & Access Scopes (Auto-generates product:create, product:view, etc.)
        class Product(Base):
            __tablename__ = "products"
            id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
            name: Mapped[str] = mapped_column()
            price: Mapped[float] = mapped_column()
            secret_cost: Mapped[float | None] = mapped_column() # Sensitive data

        # 2. Context-Aware Schema (Auto-prunes 'secret_cost' in real-time if user lacks permission)
        class ProductBase(Zchema):
            __model__ = "products"
            name: str
            price: float
            secret_cost: float | None = None

        # 3. Standardize Layers & Scaffold Router (Generates 7 secure CRUD & Search endpoints)
        class ProductRepository(BaseRepository[Product, ProductBase, ProductBase]):
            def __init__(self, db: AsyncSession):
                super().__init__(model=Product, db=db)

        class ProductService(BaseService[Product, ProductBase, ProductBase]):
            def __init__(self, repository: ProductRepository = Inject(ProductRepository)):
                super().__init__(model=Product, repository=repository)

        class ProductRouter(BaseRouter[ProductBase, ProductBase]):
            model = Product
            create_schema = ProductBase
            update_schema = ProductBase
            schema_out = ProductBase
            service = ProductService
            prefix = "/products"
    

=== "FastAPI (100+ Lines — Only 3 Basic Endpoints)"

        :::python
        # To replicate just a SUBSET of ZCore's security, transaction, and search features 
        # in raw FastAPI, you must manually write massive repetitive boilerplate:

        from fastapi import FastAPI, Depends, HTTPException, status
        from pydantic import BaseModel
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy import select, func
        import uuid

        # 1. Define Base Model
        class Product(Base):
            __tablename__ = "products"
            id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
            name: Mapped[str] = mapped_column()
            price: Mapped[float] = mapped_column()
            secret_cost: Mapped[float] = mapped_column()

        # 2. Multiple Pydantic models needed to manually prevent data leakage for different roles
        class ProductCreate(BaseModel):
            name: str
            price: float
            secret_cost: float

        class ProductOutPublic(BaseModel):
            id: uuid.UUID
            name: str
            price: float

        class ProductOutAdmin(BaseModel):
            id: uuid.UUID
            name: str
            price: float
            secret_cost: float

        # 3. Manual Create Endpoint (With manual transaction rollback)
        @app.post("/products", response_model=ProductOutAdmin)
        async def create_product(
            data: ProductCreate, 
            db: AsyncSession = Depends(get_db),
            user: User = Depends(get_current_user)
        ):
            if "product:create" not in user.scopes:
                raise HTTPException(status_code=403, detail="Access denied")
            
            product = Product(**data.model_dump())
            db.add(product)
            try:
                await db.commit() # Manual transaction commit
                await db.refresh(product)
            except Exception:
                await db.rollback() # Manual transaction rollback on failure
                raise HTTPException(status_code=400, detail="Transaction failed")
            return product

        # 4. Manual Get Endpoint (With manual role-based schema projection to prevent leaks)
        @app.get("/products/{id}")
        async def get_product(
            id: uuid.UUID, 
            db: AsyncSession = Depends(get_db),
            user: User = Depends(get_current_user)
        ):
            result = await db.execute(select(Product).where(Product.id == id))
            product = result.scalar_one_or_none()
            if not product:
                raise HTTPException(status_code=404, detail="Product not found")
            
            # Manual permission-based data pruning
            if "product:view_sensitive" in user.scopes:
                return ProductOutAdmin.model_validate(product)
            return ProductOutPublic.model_validate(product)

        # 5. Manual List Endpoint (With manual offset calculations and count queries)
        @app.get("/products")
        async def list_products(
            page: int = 1, 
            size: int = 20, 
            db: AsyncSession = Depends(get_db)
        ):
            offset = (page - 1) * size
            count_query = select(func.count()).select_from(Product)
            total = (await db.execute(count_query)).scalar_one()
            
            items_query = select(Product).offset(offset).limit(size)
            items = (await db.execute(items_query)).scalars().all()
            
            return {
                "data": [ProductOutPublic.model_validate(i) for i in items],
                "meta": {"total": total, "page": page, "size": size}
            }

---

## Instant Frontend Integration

One of ZCore's standout features is its native schema projection. By enabling a single flag on your router, you can instantly render dynamic forms on the frontend.

Adding `?schema=true` to any scaffolded POST, PUT, or PATCH endpoint returns the raw, validated JSON-Schema of that endpoint:

```bash
GET /products?schema=true
```

```json
{
  "success": true,
  "message": "Schema generated successfully",
  "data": {
    "title": "ProductBase",
    "type": "object",
    "properties": {
      "name": { "type": "string" },
      "price": { "type": "number" }
    },
    "required": ["name", "price"]
  },
  "meta": {
    "restricted_fields": []
  }
}
```

!!! info "Security Isolation"
    If the active user does not have permission to view or edit specific fields, ZCore automatically prunes those fields from the returned JSON-Schema in real-time.

---

## The Request Lifecycle

ZCore coordinates your web, context, database, and transaction layers into a single, predictable journey.

<p align="center">
  <img src="https://raw.githubusercontent.com/fastapi-zcore-framework/zcore/master/docs/assets/overview.png" 
  alt="The Request Lifecycle" width="700">
</p>


---

## Six Architectural Pillars

ZCore packages essential enterprise-grade patterns into optional, lightweight modules. 

<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1.5rem; margin: 3rem 0;">

  <div class="zcore-card" style="padding: 1.5rem; background-color: #18181b; border: 1px solid #27272a; border-radius: 0.5rem; display: flex; flex-direction: column; justify-content: flex-start;">
    <div style="font-size: 1.75rem; margin-bottom: 0.75rem;">🛡️</div>
    <h3 style="color: #f4f4f5; font-weight: 600; margin: 0 0 0.5rem 0; font-size: 1.1rem;">Context Shielding (Zchema)</h3>
    <p style="font-size: 0.875rem; color: #a1a1aa; line-height: 1.6; margin: 0;">
      Write a single schema model. ZCore dynamically prunes input fields (preventing mass assignment) and output fields (preventing data leakage) based on active user context.
    </p>
  </div>

  <div class="zcore-card" style="padding: 1.5rem; background-color: #18181b; border: 1px solid #27272a; border-radius: 0.5rem; display: flex; flex-direction: column; justify-content: flex-start;">
    <div style="font-size: 1.75rem; margin-bottom: 0.75rem;">🔗</div>
    <h3 style="color: #f4f4f5; font-weight: 600; margin: 0 0 0.5rem 0; font-size: 1.1rem;">Atomic Transactions (UOW)</h3>
    <p style="font-size: 0.875rem; color: #a1a1aa; line-height: 1.6; margin: 0;">
      Group multiple operations into a single Unit of Work. Domain events are queued and only dispatched after the database transaction commits successfully.
    </p>
  </div>

  <div class="zcore-card" style="padding: 1.5rem; background-color: #18181b; border: 1px solid #27272a; border-radius: 0.5rem; display: flex; flex-direction: column; justify-content: flex-start;">
    <div style="font-size: 1.75rem; margin-bottom: 0.75rem;">🔍</div>
    <h3 style="color: #f4f4f5; font-weight: 600; margin: 0 0 0.5rem 0; font-size: 1.1rem;">Dynamic Search Engine</h3>
    <p style="font-size: 0.875rem; color: #a1a1aa; line-height: 1.6; margin: 0;">
      A secure query builder that translates nested JSON filters, sorting, and eager-loading into safe SQL queries with depth-limit protection against DoS.
    </p>
  </div>

  <div class="zcore-card" style="padding: 1.5rem; background-color: #18181b; border: 1px solid #27272a; border-radius: 0.5rem; display: flex; flex-direction: column; justify-content: flex-start;">
    <div style="font-size: 1.75rem; margin-bottom: 0.75rem;">🏗️</div>
    <h3 style="color: #f4f4f5; font-weight: 600; margin: 0 0 0.5rem 0; font-size: 1.1rem;">Scoped DI Container</h3>
    <p style="font-size: 0.875rem; color: #a1a1aa; line-height: 1.6; margin: 0;">
      Clean constructor-based dependency injection. Registers singletons, transients, and request-scoped dependencies that are auto-cleaned per request.
    </p>
  </div>

  <div class="zcore-card" style="padding: 1.5rem; background-color: #18181b; border: 1px solid #27272a; border-radius: 0.5rem; display: flex; flex-direction: column; justify-content: flex-start;">
    <div style="font-size: 1.75rem; margin-bottom: 0.75rem;">🚀</div>
    <h3 style="color: #f4f4f5; font-weight: 600; margin: 0 0 0.5rem 0; font-size: 1.1rem;">Progressive Routing</h3>
    <p style="font-size: 0.875rem; color: #a1a1aa; line-height: 1.6; margin: 0;">
      Scaffold 7 CRUD and search endpoints in seconds, or bypass the router completely to write standard, raw FastAPI functional endpoints.
    </p>
  </div>

  <div class="zcore-card" style="padding: 1.5rem; background-color: #18181b; border: 1px solid #27272a; border-radius: 0.5rem; display: flex; flex-direction: column; justify-content: flex-start;">
    <div style="font-size: 1.75rem; margin-bottom: 0.75rem;">📦</div>
    <h3 style="color: #f4f4f5; font-weight: 600; margin: 0 0 0.5rem 0; font-size: 1.1rem;">Topological Plugins</h3>
    <p style="font-size: 0.875rem; color: #a1a1aa; line-height: 1.6; margin: 0;">
      Structure your codebase into clean modules. The central kernel automatically sorts and loads plugins based on their declared dependencies.
    </p>
  </div>

</div>

---

## Built for Absolute Freedom

Is ZCore another rigid framework like Django? **No.**

We believe in **progressive disclosure**. You only use what you need, when you need it. If a specific business route requires raw, custom logic, bypass the scaffolding router entirely while still using ZCore's decoupled background layers:

```python
# Bypass the scaffolding BaseRouter and write standard, functional FastAPI
@app.post("/custom-checkout")
async def checkout(
    data: CheckoutRequest,
    checkout_service: CheckoutService = Inject(CheckoutService) # Still uses Scoped DI
):
    # Execute transactional business logic
    return await checkout_service.process_order(data)
```

!!! success "Next Steps"
    Ready to experience clean FastAPI architecture? Proceed to the [Installation & Scaffolding](learn/installation/) guide to create your first ZCore app in seconds.