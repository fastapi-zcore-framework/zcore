# WebSocket Streaming

Deliver real-time events to authenticated users through Redis PubSub with automatic local fallback, bounded queue protection, and safe subscription lifecycle management.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>Real-Time Messaging</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Status</span><br>
    <strong>Optional Ecosystem</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Underlying Tech</span><br>
    <strong>Redis PubSub / asyncio.Queue</strong>
  </div>
</div>

## The Challenge

Building real-time user-targeted event streaming in a horizontally-scaled web application introduces several hard problems:

1.  **Multi-Node Broadcast:** In a standard setup, a WebSocket connection is pinned to a single server process. An event generated on Node A cannot reach a user connected to Node B without a shared backplane.
2.  **Queue Overrun:** Naive in-process queues grow unboundedly when a slow consumer cannot keep up, eventually exhausting memory and crashing the worker.
3.  **Subscription Leaks:** When a WebSocket disconnects, the associated event listener must be cleaned up. Failing to do so results in ghost subscriptions that keep processing and queuing events for connections that no longer exist.

## The ZCore Elegance

The `StreamManager` provides a subscription-based event streaming system. It maintains a per-user mapping of bounded `asyncio.Queue` instances, routes published events through Redis PubSub to broadcast across all application nodes, and falls back to local in-memory delivery when Redis is unavailable.

=== "ZCore Real-Time Streaming"
        :::python
        from zcore.web.streams import StreamManager
        from zcore.web.api_router import ZCoreAPIRoute

        stream_manager = StreamManager()

        @app.websocket("/ws/events")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            user_id = get_authenticated_user_id(websocket)

            # 1. Subscribe via safe context manager
            async with stream_manager.subscription(user_id) as queue:
                while True:
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=30)
                        await websocket.send_json(event)
                    except asyncio.TimeoutError:
                        await websocket.send_json({"type": "heartbeat"})

        # Publish from any service (any node)
        await stream_manager.publish(user_id, {"type": "order_update", "order_id": "123"})

=== "Standard WebSocket Handling"
        :::python
        # Single-node only, no cluster support
        active_connections: dict[uuid.UUID, list[WebSocket]] = {}

        @app.websocket("/ws")
        async def ws(websocket: WebSocket):
            user_id = extract_user(websocket)
            active_connections.setdefault(user_id, []).append(websocket)
            try:
                while True:
                    data = await websocket.receive_text()
                    # No Redis backplane — cannot reach other nodes
            except WebSocketDisconnect:
                # Manual cleanup—easy to forget or mis-handle
                if user_id in active_connections:
                    active_connections[user_id].remove(websocket)

---

## Streaming Architecture

<p align="center">
  <img src="https://raw.githubusercontent.com/fastapi-zcore-framework/zcore/master/docs/assets/stream.png" 
  alt="Streaming Architecture" width="700">
</p>


---

## Boundaries & Integration

The streaming layer is designed for horizontal scalability and clean lifecycle management.

*   **Redis PubSub Fallback:** The `publish` method attempts Redis first. If Redis is not configured or the call fails (timeout, connection refused), the event is routed locally via `_local_publish`. This ensures that streaming works in development without Redis and degrades gracefully in production during Redis outages.
*   **Dependency Injection Friendly:** `StreamManager` is a plain Python class that can be registered as a singleton in the IoC container. Its `publish` method can be injected into any service or background task without coupling to the Web layer.
*   **WebSocket Agnostic:** The `StreamManager` has no dependency on `WebSocket` or `Starlette`. It manages `asyncio.Queue` objects keyed by `uuid.UUID`. This allows it to be used with custom protocols, SSE (Server-Sent Events), or long-polling implementations.

---

## Under-the-Hood Spec

### 1. Redis PubSub Backplane with Pattern Subscription

The `StreamManager` subscribes to the Redis pattern `stream:user:*` using `psubscribe` [web/streams.py]. This is a single subscription that matches all user-specific channels. When a message arrives, the handler parses the user ID from the channel name (`channel.split(":")[-1]`) and forwards the JSON-deserialized payload to the matching local queues.

### 2. Bounded Queue Overflow Protection

Each user subscription creates an `asyncio.Queue(maxsize=100)` [web/streams.py]. When `_local_publish` distributes an event, it calls `queue.put_nowait(data)`. If the queue is full, `put_nowait` raises `asyncio.QueueFull`. The handler catches this and **removes the overflowing queue** from the active list, effectively disconnecting the slowest consumer for that user. This prevents one slow WebSocket from causing memory exhaustion for the entire process.

### 3. Subscription Context Manager with Guaranteed Cleanup

The `subscription(user_id)` method is an `@asynccontextmanager` [web/streams.py]. It calls `subscribe` on entry (which creates the queue and starts the Redis PubSub listener if needed) and `unsubscribe` on exit (which removes the queue from the user's list and cancels the PubSub background task if no more active queues exist). This pattern guarantees cleanup even if the WebSocket handler raises an unhandled exception.

### 4. Background Listener Lifecycle

`start_listening` initializes the Redis PubSub connection and spawns `_listen_to_redis` as a background `asyncio.Task` [web/streams.py]. The task runs until cancelled. In the `finally` block, it always calls `punsubscribe` and `close()` on the PubSub connection, ensuring Redis resources are released. The task is lazily started on the first `subscribe` call and automatically cancelled in `unsubscribe` when the last queue is removed.

### 5. Thread-Safe Queue State with Async Lock

All mutations to the `users_queues` dictionary are protected by `self._lock`, an `asyncio.Lock` [web/streams.py]. This prevents race conditions where a concurrent `publish` and `unsubscribe` could modify the same user's queue list simultaneously in an async context.

!!! info "Redis Client Isolation"
    The streaming subsystem maintains its own module-level `_stream_redis_client`, separate from the caching layer's `_shared_redis_client`. Each subsystem manages its own connection lifecycle and configuration.

!!! tip "Horizontal Scaling"
    To scale WebSocket streams across multiple application instances, ensure all instances share the same Redis instance. Each node subscribes to the same `stream:user:*` pattern via its own PubSub connection, guaranteeing that an event published on any node reaches the user regardless of which node they are connected to.