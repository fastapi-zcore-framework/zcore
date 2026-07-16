# WebSocket & Redis PubSub

Multi-subscriber real-time event streaming with cluster-wide broadcasting and automated backpressure management.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>Real-time Streaming</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Status</span><br>
    <strong>Optional Utility</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Underlying Tech</span><br>
    <strong>asyncio.Queue / Redis PubSub</strong>
  </div>
</div>

## The Challenge
Scaling WebSockets in a distributed environment (multiple server instances) is complex. If **User A** is connected via WebSocket to **Server 1**, but a relevant event (like a new message) is processed by **Server 2**, Server 2 has no direct way to reach the socket on Server 1. 

Furthermore, managing these connections in raw FastAPI requires:
1.  **Manual PubSub Wiring:** Subscribing to Redis channels and correctly parsing messages.
2.  **Memory Leak Risks:** Forgetting to unregister listeners when a WebSocket disconnects.
3.  **Slow Consumer Protection:** Preventing a slow client from filling up the server's memory with unsent messages.

## The ZCore Elegance
The `StreamManager` provides a unified interface for local and distributed events. It uses a **Subscription Context Manager** that automatically handles registration, Redis PubSub pattern-matching, and silent cleanup upon disconnection. It implements an internal backpressure policy that automatically evicts "stuck" listeners to preserve system stability.

=== "ZCore Stream Subscription"
        :::python
        from zcore.web import StreamManager
        from fastapi import WebSocket

        stream_manager = StreamManager()

        @app.websocket("/ws/{user_id}")
        async def websocket_endpoint(websocket: WebSocket, user_id: uuid.UUID):
            await websocket.accept()
            
            # 1. Atomic Subscription & Auto-Cleanup
            async with stream_manager.subscription(user_id) as queue:
                try:
                    while True:
                        # 2. Non-blocking retrieval
                        data = await queue.get()
                        await websocket.send_json(data)
                except WebSocketDisconnect:
                    pass 
            # 3. Context manager ensures unsubscription from Redis/Local memory

=== "FastAPI Raw Implementation"
        :::python
        # Manual management across multiple server instances
        @app.websocket("/ws/{user_id}")
        async def websocket_endpoint(websocket: WebSocket, user_id: uuid.UUID):
            await websocket.accept()
            pubsub = redis.pubsub()
            await pubsub.subscribe(f"user:{user_id}")
            
            try:
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        await websocket.send_json(json.loads(message["data"]))
            finally:
                # 1. Manual cleanup is easy to forget
                # 2. No protection against slow consumer backpressure
                # 3. No easy way to broadcast to local queues without Redis
                await pubsub.unsubscribe(f"user:{user_id}")

---

## Boundaries & Integration
ZCore manages the routing logic, leaving the transport to FastAPI.

*   **Transport Agnostic:** The `StreamManager` provides a standard `asyncio.Queue`. While designed for WebSockets, you can use it for Server-Sent Events (SSE) or long-polling.
*   **Redis Optional:** If `init_stream_redis` is not called, the manager operates in "Local-Only" mode—perfect for development or single-node deployments.
*   **Structured Serialization:** All messages routed through the manager are automatically serialized/deserialized using ZCore's `CustomJSONEncoder`, supporting UUIDs and Datetime out of the box [utils/helpers.py].

---

## Under-the-Hood Spec

### 1. Cluster-Wide Pattern Matching
The `StreamManager` uses `psubscribe` with the pattern `stream:user:*` [web/streams.py]. Instead of creating a unique Redis subscription for every single user (which is expensive), ZCore maintains a single background task (`_listen_to_redis`) that multiplexes incoming cluster-wide messages to the correct local memory queues based on the channel name.

### 2. Backpressure & Eviction Policy
To prevent memory exhaustion, every user queue has a `maxsize=100` [web/streams.py]. When publishing, ZCore uses `queue.put_nowait()`. If a queue is full (meaning the client is too slow to receive messages), ZCore **evicts the queue immediately** and logs a warning. This "fail-fast" approach protects the server's memory from being consumed by stale or hung connections.

### 3. Thread-Safe State Management
All modifications to the internal `users_queues` mapping are protected by an `asyncio.Lock` [web/streams.py]. This prevents race conditions where a user might be unsubscribed while a message is simultaneously being routed to them from the Redis background task.

!!! info "Redis Scalability"
    By utilizing the `init_stream_redis` hook, you can share a single Redis connection pool between your Cache, Database (if using Redis), and Stream Manager, optimizing your infrastructure's connection count.