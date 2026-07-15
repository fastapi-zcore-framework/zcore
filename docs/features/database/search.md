# Dynamic Search Engine

Securely translate structured JSON filters, complex sorting, and relational eager-loading into optimized SQLAlchemy queries.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>Query Utility</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Status</span><br>
    <strong>Recommended</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Underlying Tech</span><br>
    <strong>SQLAlchemy 2.0 / Pydantic</strong>
  </div>
</div>

## The Challenge
Building a truly dynamic search endpoint (e.g., `POST /products/search`) in standard FastAPI is a security and maintenance nightmare. Developers often face:
1.  **Manual Filter Mapping:** Writing endless `if` statements for every possible combination of `price_gt`, `category_eq`, or `name_ilike`.
2.  **Unsafe Joins:** Manually managing table joins for relational filters, often leading to duplicate rows or Cartesian products.
3.  **Recursive DoS:** Deeply nested "OR" and "AND" JSON filters that can crash a database if the query complexity isn't limited.
4.  **Security Leaks:** Clients accidentally filtering or sorting by restricted fields (like `margin` or `internal_id`) that should be hidden from their role.

## The ZCore Elegance
The `SearchEngine` provides a secure, JSON-driven query builder. It parses a `SearchRequest` object containing nested filters, sorting rules, and relation-preload paths. It automatically coerces types, validates the request against active context restrictions, and limits the query depth to prevent resource exhaustion.

=== "ZCore Dynamic Search"
        :::python
        from zcore.db import SearchRequest, SearchEngine

        # 1. Define a structured search payload
        request = SearchRequest(
            filters=[
                {"field": "price", "op": "gt", "value": 100},
                {"op": "or", "items": [
                    {"field": "category.name", "op": "eq", "value": "Electronics"},
                    {"field": "tags", "op": "ilike", "value": "premium"}
                ]}
            ],
            include=["category", "tags"],
            sort=[{"field": "price", "order": "desc"}]
        )

        # 2. Build and execute securely via Repository
        results = await product_repository.search(request)

=== "FastAPI Raw Manual Filtering"
        :::python
        # Replicating dynamic logic requires hundreds of lines:
        @router.get("/search")
        async def manual_search(
            price_gt: float = None, 
            category: str = None,
            db: AsyncSession = Depends(get_db)
        ):
            query = select(Product)
            if price_gt:
                query = query.where(Product.price > price_gt)
            if category:
                query = query.join(Category).where(Category.name == category)
            
            # Manually handling nested OR/AND is almost impossible
            # to write safely and generically for every endpoint.
            result = await db.execute(query)
            return result.scalars().all()

---

## Search Workflow
The `SearchEngine` validates and compiles the request through a strict security-first pipeline.

<p align="center">
  <img src="https://raw.githubusercontent.com/fastapi-zcore-framework/zcore/master/docs/assets/search.png" 
  alt="Search Workflow" width="700">
</p>


---

## Boundaries & Integration
ZCore provides a dynamic bridge without locking you out of SQLAlchemy's native power.

*   **Select Object Return:** The core engine method `build_base_query()` returns a standard SQLAlchemy `Select` object. You can still apply additional `.where()` clauses or `.limit()` before execution.
*   **Custom Handlers:** If a specific field requires complex custom logic (e.g., a full-text search vector), you can register a custom handler: `engine.register_handler("full_text", my_handler_func)`.
*   **Bypass:** If you only need simple primary key lookups, use the repository's `get()` or `get_by_ids()` methods instead of the search engine to save processing overhead.

---

## Under-the-Hood Spec

### 1. Recursive Depth Protection
To defend against "Recursive DoS" attacks, the `SearchEngine` enforces a `max_depth` limit (default: 3) [db/search.py]. If a client sends a JSON payload with more than 3 levels of nested `or`/`and` operators, the engine raises a `ValidationError` before any SQL is generated.

### 2. Intelligent Loader Strategy
The engine automatically chooses the most efficient SQLAlchemy loader [db/search.py]. It inspects the model relations:
-   **`joinedload`**: Used for many-to-one or one-to-one relationships to minimize queries.
-   **`selectinload`**: Used for one-to-many or many-to-many collections to avoid Cartesian products and "N+1" problems.

### 3. Safe Type Coercion
Since JSON sends everything as primitives (strings/numbers), the engine uses model inspection to coerce values [db/search.py]. It automatically detects if a target column is a `uuid.UUID`, `date`, or `datetime` and attempts to parse the incoming string using ISO 8601 standards before creating the comparison expression.

### 4. Wildcard Sanitization
For `ilike` operations, ZCore automatically escapes SQL-sensitive wildcards (`%`, `_`, `\`) [db/search.py]. This prevents clients from performing "blind" wildcard searches that could lead to full-table scans and performance degradation.

!!! info "Security Isolation"
    The SearchEngine is strictly integrated with `zcore.context`. If a field dot-path (e.g., `category.secret_code`) is restricted in the active user context, any attempt to filter, sort, or include that field will result in a `ForbiddenError`.