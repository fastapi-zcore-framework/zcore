# 📋 Step 2: Pydantic Schemas

While the database model represents how data is **stored**, Pydantic schemas represent how data is **transported**. This modest separation ensures that internal database logic remains decoupled from the external API contract, providing a safety buffer for your data.

Open `products/schemas.py` and define the following contracts:

```python
import uuid
from decimal import Decimal
from typing import Optional
from pydantic import Field, ConfigDict
from zcore import Zchema

class ProductBase(Zchema):
    """Shared attributes validated across incoming and outgoing product requests."""
    __db_name__ = "product"
    name: str = Field(..., min_length=2, max_length=120, description="Product retail name")
    price: Decimal = Field(..., ge=0.00, max_digits=10, decimal_places=2, description="Product price")
    stock: int = Field(default=0, ge=0, description="Available stock inventory")

class ProductCreate(ProductBase):
    """Schema for validating new product creation payloads."""
    pass

class ProductUpdate(Zchema):
    """Schema for validating product update payloads (supports partial patches)."""
    __db_name__ = "product"
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    price: Optional[Decimal] = Field(None, ge=0.00, max_digits=10, decimal_places=2)
    stock: Optional[int] = Field(None, ge=0)

class ProductResponse(ProductBase):
    """Schema representing the serialized API response payload."""
    id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)
```

---

## 🛠️ Schema Responsibility Matrix

To help understand when to use each schema, refer to this breakdown:

| Schema Name | Direction | Primary Responsibility |
| :--- | :--- | :--- |
| 📦 `ProductCreate` | **Inbound** | Validates that name, price, and stock exist and meet constraints. |
| 🛠️ `ProductUpdate` | **Inbound** | Allows clients to update only specific fields (Optionality). |
| 📤 `ProductResponse` | **Outbound** | Formats the data for the client and includes the generated `id`. |

---

## 🔐 The `Zchema` Base Class

All schemas in ZCore should inherit from `Zchema` (not directly from Pydantic's `BaseModel`). `Zchema` is a drop-in replacement that adds three layers of automatic security:

| Tier | Mechanism | What It Protects |
| :--- | :--- | :--- |
| **1. Dynamic Schema Generation** | `__get_pydantic_json_schema__` | Removes restricted fields when clients request `?schema=true`. |
| **2. Input Validation** | `model_validator` | Silently strips restricted fields from incoming request payloads (prevents Mass Assignment). |
| **3. Response Pruning** | `model_serializer` | Strips restricted fields from the final outgoing JSON response. |

### 🏷️ The `__db_name__` Attribute

Every `Zchema` subclass must define a `__db_name__` class attribute that binds the schema to its database domain (e.g., `"product"`, `"user"`, `"order"`). This enables the security layer to resolve restricted field paths like `product.price` or `user.email` without namespace collisions across different modules.

```python
class ProductBase(Zchema):
    __db_name__ = "product"   # <-- domain binding
    name: str
```

---

## 💰 Engineering Note: Why `Decimal`?

!!! tip "💡 Precision in Financial Data"
    In ZCore, we prefer `decimal.Decimal` over `float` for monetary values like `price`. Floating-point arithmetic can lead to rounding errors (e.g., `0.1 + 0.2` not equaling `0.3`), which is unacceptable in financial systems. Pydantic handles the conversion from JSON numbers to Python Decimals transparently.

---

## 🔗 Integration with SQLAlchemy

!!! note "🛡️ The Role of `from_attributes`"
    In Pydantic V2, setting `model_config = ConfigDict(from_attributes=True)` enables the schema to parse data directly from database models. Instead of manually mapping SQLAlchemy fields to dictionary keys, Pydantic reads properties directly from the ORM object, even when attributes are loaded lazily.

Now that our data layers (Database and Schema) are defined, we will create the **Repository Layer** to handle SQL operations for us.