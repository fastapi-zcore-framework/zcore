# Distributed Caching

Accelerate response times with a transparent, dual-layer caching system that routes through Redis and falls back to a thread-safe in-memory LRU store with automatic TTL eviction.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>Performance Layer</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Status</span><br>
    <strong>Optional Ecosystem</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Underlying Tech</span><br>
    <strong>Redis / OrderedDict + threading</strong>
  </div>
</div>

## The Challenge

Caching in an async Python application introduces several subtle failure modes:

1.  **Cache Stampede Risk:** When the distributed cache (Redis) goes down, every request hits the database simultaneously, overwhelming the connection pool.
2.  **Type Corruption:** Serialized JSON blobs are returned as raw dictionaries. Consumers must manually validate or cast the data back to the expected Pydantic model, often leading to `AttributeError` at runtime.
3.  **Memory Leaks:** Naive in-memory caches keep references to objects indefinitely. In long-running async workers, this causes unbounded memory growth and eventual OOM kills.
4.  **Stale Data Propagation:** Expired keys linger in memory until explicitly checked, returning stale data to users.

## The ZCore Elegance

ZCore provides `BaseCache`, a generic interface that transparently routes reads and writes through Redis when available, falling back to a local `TTLLRUCache` with thread-safe access, automatic TTL expiry, and weak-reference tracking for global eviction sweeps.

=== "ZCore Dual-Layer Caching"
        :::python
        from zcore.cache import BaseCache, init_cache, close_cache

        # 1. Initialize Redis (optional) and eviction loop
        await init_cache(redis_url="redis://localhost:6379/0")

        # 2. Create a typed cache for a domain
        product_cache = BaseCache[ProductOut](prefix="products")

        # 3. Cache-aside pattern with automatic Pydantic validation
        async def get_product(id: uuid.UUID) -> ProductOut:
            cached = await product_cache.get(str(id), target_type=ProductOut)
            if cached:
                return cached
            product = await fetch_from_db(id)
            await product_cache.set(str(id), product.model_dump(), ttl=300)
            return product

        # 4. Graceful shutdown
        await close_cache()

=== "Standard Manual Caching"
        :::python
        import json
        import redis.asyncio as aioredis
        from functools import lru_cache

        # Manual Redis client with no fallback
        client = aioredis.from_url("redis://localhost:6379/0")

        @lru_cache(maxsize=128)  # No TTL, no thread-safety in async
        async def get_product(id: uuid.UUID) -> ProductOut:
            raw = await client.get(f"product:{id}")
            if raw:
                data = json.loads(raw)
                return ProductOut(**data)  # No validation, no fallback on Redis failure
            product = await fetch_from_db(id)
            await client.set(f"product:{id}", product.model_dump_json(), ex=300)
            return product

        # Redis failure → all requests hit DB → stampede
        # lru_cache is not async-safe
        # No global cleanup mechanism

---

## Cache Resolution Strategy

<p align="center">
  <img src="https://raw.githubusercontent.com/fastapi-zcore-framework/zcore/master/docs/assets/cache.png" 
  alt="Cache Resolution Strategy" width="700">
</p>

---

## Boundaries & Integration

The caching layer is fully optional and designed to be composed with other ZCore components.

*   **Pydantic-First:** The `get` method accepts an optional `target_type` parameter. If a Pydantic model is provided, the deserialized dictionary is validated through `model_validate` before being returned. This guarantees type safety without manual casting.
*   **Prefix Isolation:** Each `BaseCache` instance is created with a `prefix` string (e.g., `"products"`). All keys are automatically namespaced as `{prefix}:{key}`, preventing collision between different cache domains sharing the same Redis instance.
*   **Background Eviction:** `init_cache` schedules a background `asyncio.Task` that runs every 60 seconds, calling `TTLLRUCache.evict_all_expired()` to purge stale records from all active in-memory cache instances.

---

## Under-the-Hood Spec

### 1. BaseCache / TTLLRUCache Fallback Architecture

`BaseCache` holds a reference to a `TTLLRUCache` instance (default `maxsize=1000`) as `_local_cache` [cache/base.py]. On `set`, the method attempts Redis first. If Redis is unavailable or raises an exception (connection refused, timeout, etc.), the serialized value is written to the local LRU store. On `get`, the method tries Redis, then falls back to the local cache.

### 2. Pydantic Type Validation on Cache Hits

When `target_type` is provided and is a `BaseModel` subclass, the `get` method calls `target_type.model_validate(parsed_data)` [cache/base.py]. This ensures that the deserialized payload conforms exactly to the expected schema. If validation fails (e.g., due to schema drift between cache writes and reads), `None` is returned and the miss is treated as a cache miss.

### 3. Eviction Loop Safety

The global eviction loop `_start_eviction_loop` runs as a background `asyncio.Task` [cache/base.py]. It catches `asyncio.CancelledError` to exit cleanly and wraps the eviction call in a generic `except Exception` to prevent a single faulty cache instance from crashing the entire loop.

### 4. WeakRef Active Cache Registry

`TTLLRUCache` registers every new instance in a module-level `weakref.WeakSet` called `_active_caches` [cache/ttllru_cache.py]. This enables `evict_all_expired` to iterate over all existing cache instances without preventing garbage collection of discarded instances. When an instance is garbage collected, its weak reference is automatically removed from the set.

### 5. Thread-Safe LRU with Reentrant Lock

Each `TTLLRUCache` instance uses a `threading.Lock` to protect all read and write operations [cache/ttllru_cache.py]. The underlying storage is an `OrderedDict` mapping keys to `(expiry_timestamp, value)` tuples. On `get`, expired keys are detected inline by comparing `time.time()` against the stored expiry, and are popped before `move_to_end` slides the remaining entry to the front.

!!! info "Redis Dependency"
    The `BaseCache` Redis client (`redis.asyncio`) is imported lazily. If `redis` is not installed, `REDIS_AVAILABLE` is set to `False` and the cache operates exclusively in local fallback mode without raising import errors.

!!! tip "Sizing the Local Cache"
    The local `TTLLRUCache` defaults to a `maxsize` of 1000 entries. Adjust this in environments with high cardinality but limited memory. The LRU policy ensures that the most recently accessed items are always available.