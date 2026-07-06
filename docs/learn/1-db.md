# 🗄️ Step 1: Database Models

Following our bottom-up development flow, we start at the physical database representation. In ZCore, database models are defined using asynchronous SQLAlchemy 2.0 declarative mappers.

Open `products/models.py` and replace its contents with the following:

```python
import uuid
from sqlalchemy import String, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from zcore.db.setup import Base

class Product(Base):
    """Database representation of our Product catalog."""
    
    __tablename__ = "products"
    
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, 
        default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(
        String(120), 
        nullable=False, 
        index=True
    )
    price: Mapped[float] = mapped_column(
        Numeric(10, 2), 
        nullable=False, 
        default=0.0
    )
    stock: Mapped[int] = mapped_column(
        Integer, 
        nullable=False, 
        default=0
    )
```

---

## 📊 Database Column Schema

For reference, here is how our `Product` Python model maps directly to the underlying SQL database columns:

| Python Property | SQL Column Type | Nullable | Default / Behavior |
| :--- | :--- | :--- | :--- |
| 🆔 `id` | `UUID` | ❌ No | Primary Key, Auto-generated UUIDv4 |
| 📝 `name` | `VARCHAR(120)` | ❌ No | Indexed for high-performance searches |
| 💰 `price` | `NUMERIC(10, 2)` | ❌ No | `0.0` (Uses precise decimal scale) |
| 📦 `stock` | `INTEGER` | ❌ No | `0` (Represents physical inventory) |

---

## 🛡️ Why ZCore Recommends UUIDs

!!! info "🛡️ Distributed Identifier Security"
    ZCore uses `uuid.UUID` (specifically UUIDv4) as the default primary key instead of auto-incrementing integers. 
    Sequential integer IDs (`1, 2, 3...`) expose business metrics (e.g., total products or orders) through simple iteration, and are vulnerable to malicious URL scanning. UUIDs provide distributed identifier safety, allowing you to generate safe IDs client-side or on decoupled nodes without risk of primary key collisions.

---

## 📋 Declaring Table Metadata

By inheriting from `Base`, the `Product` model is automatically registered with the metadata engine. This allows it to work with SQLAlchemy's async migration patterns and gives it access to ZCore's declarative permission mappings:

```python
# ZCore automatically generates table permission actions:
# Product.actions().VIEW   -> "products:view"
# Product.actions().CREATE -> "products:create"
```

In the next step, we will define the Pydantic schemas that validate data payload boundaries for these model fields.