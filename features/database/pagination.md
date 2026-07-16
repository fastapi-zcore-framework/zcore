# Page-Number & Keyset Pagination

High-performance dataset navigation with stable cursors, optimized count queries, and standardized metadata.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>Infrastructure Layer</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Status</span><br>
    <strong>Core Capability</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Underlying Tech</span><br>
    <strong>SQLAlchemy 2.0 / Base64</strong>
  </div>
</div>

## The Challenge
Implementing pagination in FastAPI often results in "Leaky Implementation Details" and performance bottlenecks:
1.  **Offset Drift:** In standard `LIMIT/OFFSET` pagination, if a new record is inserted while a user is on page 2, the same item may appear again on page 3.
2.  **Count Inefficiency:** Running a `SELECT COUNT(*)` on a table with millions of rows every time a user navigates can slow down the entire database.
3.  **Inconsistent Metadata:** Different endpoints returning different structures for `total`, `has_next`, or `page_size`, making frontend integration difficult.
4.  **Complex Sorting:** Manually writing the SQL logic to sort by dynamic fields while ensuring stable ordering.

## The ZCore Elegance
ZCore provides two standardized pagination engines: **Page-Number** (Offset-based) for small-to-medium datasets, and **Cursor** (Keyset-based) for high-performance, stable navigation in large datasets. Both engines are integrated into `BaseRepository` and use Pydantic models for strict parameter validation.

=== "ZCore Repository Pagination"
        :::python
        from zcore.db import PageNumberParams, CursorParams

        # 1. Page-Number (Offset) Navigation
        params = PageNumberParams(page=1, size=20, sort_by="created_at")
        result = await repository.get_list(pagination=params)
        # result.meta -> {total, page, total_pages, has_next, ...}

        # 2. Cursor (Keyset) High-Performance Navigation
        cursor_params = CursorParams(size=50, cursor="encoded_string...")
        result = await repository.get_list(pagination=cursor_params)
        # result.meta -> {next_cursor, has_more, size}

=== "FastAPI Raw Offset Implementation"
        :::python
        # Manual offset calculations and count queries
        @app.get("/items")
        async def get_items(page: int = 1, size: int = 20, db: AsyncSession = Depends(get_db)):
            offset = (page - 1) * size
            
            # Manual count query
            total = (await db.execute(select(func.count()).select_from(Item))).scalar()
            
            # Manual data query
            query = select(Item).offset(offset).limit(size)
            items = (await db.execute(query)).scalars().all()
            
            return {
                "data": items,
                "meta": {"total": total, "page": page, "size": size}
            }

---

## Boundaries & Integration
The pagination engine is built to handle raw SQLAlchemy queries without requiring ZCore-specific models.

*   **Select Object Support:** Both `paginate` methods accept a standard SQLAlchemy `Select` object [db/pagination.py]. You can apply complex joins and filters before passing the query to the paginator.
*   **Pydantic Models:** The parameters `PageNumberParams` and `CursorParams` are standard Pydantic models. You can inherit from them to add custom filters or stricter validation.
*   **Bypass:** If you require a non-standard pagination logic (e.g., specialized window functions), you can bypass the paginator and execute your own query using the repository's `db` session.

---

## Under-the-Hood Spec

### 1. The `order_by(None)` Count Optimization
When calculating the total count for Page-Number pagination, ZCore clones the original query and strips the `ORDER BY` clause using `.order_by(None)` [db/pagination.py]. This is a critical database optimization because the database engine does not need to perform expensive sorting just to count the number of rows that match the filters.

### 2. Base64 Cursor Keyset
`CursorPagination` generates an opaque, URL-safe Base64 string for navigation [db/pagination.py]. This cursor contains a JSON payload with the sorting value (e.g., a timestamp) and the primary key (UUID) to act as a tie-breaker. This ensures that even if two items have the exact same timestamp, the pagination remains stable and unique.

### 3. Date & Time ISO Transformation
The cursor encoder automatically detects `datetime` objects [db/pagination.py]. It ensures they are converted to UTC and serialized in ISO 8601 format before being Base64 encoded. This guarantees that cursors generated on one server instance can be safely decoded on another, regardless of local server time settings.

### 4. Tie-Breaker Logic (desc/asc)
To prevent "skipped" items, the cursor query uses a tuple-comparison approach [db/pagination.py]. For a descending sort, it generates a query like: `WHERE (col < last_val) OR (col == last_val AND pk < last_pk)`. This ensures that every single record is visited in a deterministic order.

!!! info "Cursor UI"
    Because cursors are opaque strings, they are ideal for "Infinite Scroll" or "Load More" UI patterns. Use Page-Number pagination only when the user needs to jump to a specific numbered page (e.g., "Go to page 15").