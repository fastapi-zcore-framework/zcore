# 🚀 Step 8: Bootstrapping the Application

We have reached the final modest step of our bottom-up quickstart guide. In this stage, we will assemble all our components—the database manager, the core kernel, and our domain plugins—into a single entry point: `main.py`.

Open `main.py` and replace its contents with the following assembly:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI
from zcore import Kernel, settings
from zcore.web import RequestLogMiddleware, ScopedDependencyMiddleware
from zcore.exceptions import app_exception_handler, AppException
from zcore.db import db_manager, register_db_event_dispatcher
from zcore.logging import setup_logging

# Import our custom domain plugin
from products.plugin import ProductPlugin

# 1. Initialize Structured Logging
setup_logging()

# 2. Configure our Database Manager (Async SQLite Engine)
db_manager.init_app(
    db_url=settings.DATABASE_URL,
    pool_size=settings.POOL_SIZE,
    max_overflow=settings.MAX_OVERFLOW,
    echo=(settings.ENVIRONMENT == "development")
)

# 3. Create the Core Kernel and register plugins
kernel = Kernel()
kernel.add_plugin(ProductPlugin())

# 4. Register the global database event dispatcher
register_db_event_dispatcher(kernel.dispatcher)

# 5. Initialize the FastAPI app and hook the kernel's lifespan
app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=kernel.lifespan
)

# 6. Apply core middlewares
app.add_middleware(RequestLogMiddleware)
app.add_middleware(ScopedDependencyMiddleware)

# 7. Apply the centralized error handler
app.add_exception_handler(AppException, app_exception_handler)

# 8. Setup plugin routes
kernel.setup(app)

@app.get("/")
async def root():
    return {
        "status": "healthy",
        "framework": "ZCore",
        "environment": settings.ENVIRONMENT
    }
```

---

## 🏗️ The Bootstrapping Sequence

Understanding the order of operations helps in maintaining a predictable system. Here is what happens when you start this script:

| Phase | Responsibility | Why it matters |
| :--- | :--- | :--- |
| 🪵 **Logging** | `setup_logging()` | Standardizes logs into JSON or Console format. |
| 🗄️ **Database** | `db_manager.init_app()` | Warms up the async connection pool. |
| 🧠 **Kernel** | `Kernel()` | Prepares the dependency graph for your plugins. |
| 🛡️ **Security** | `Middlewares` | Manages Request-IDs and Scoped DI boundaries. |
| 🚦 **Lifespan** | `kernel.lifespan` | Orchestrates the `on_startup` and `on_shutdown` hooks. |

---

## 💻 Launching the Server

With the entry point configured, you can launch the local development server using the ZCore CLI. Ensure your virtual environment is active:

```bash
zc run
```

You should see log output indicating that Uvicorn has started on `http://127.0.0.1:8000`.

---

## ✅ Quickstart Success Checklist

To verify that your Product Management System is running as intended, check the following:

*   [ ] **API Health Check:** Open `http://127.0.0.1:8000/` in your browser. You should receive: `{"status": "healthy", ...}`.
*   [ ] **Swagger UI:** Navigate to `http://127.0.0.1:8000/docs`. You will see the auto-generated documentation for the `/products` CRUD suite.
*   [ ] **Database Generation:** Since SQLite is our default, ZCore will automatically create a `zcore_dev.db` file in your root folder upon the first request.

```text
📁 product_api/
├── products/          ← Your domain module
├── main.py            ← Assembly point
├── zcore_dev.db       ← Generated SQLite database
├── .env               ← Configuration
└── requirements.txt   ← Project dependencies
```

---

## 💡 Engineering Insights

!!! tip "💡 Response Customization"
    If you want to change the database or server port, you don't need to touch `main.py`. Simply update the values in your `.env` file. ZCore's `settings` proxy will automatically pick up the changes.

!!! info "🛡️ Middleware Safety"
    The `ScopedDependencyMiddleware` is critical. It ensures that every HTTP request gets its own isolated "sandbox" for database sessions and services. When the request ends, ZCore automatically cleans up these resources to prevent memory leaks.

---

**Congratulations!** You have successfully built a modular, type-safe, and architecturally sound API using ZCore. 

From here, you can add more plugins, implement complex business logic in your services, or explore the **Unit of Work** pattern for managing multiple database operations in a single transaction.