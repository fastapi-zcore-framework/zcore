# 📋 Step 2: Pydantic Schemas

While the database model represents how data is **stored**, Pydantic schemas represent how data is **transported**. This modest separation ensures that internal database logic remains decoupled from the external API contract, providing a safety buffer for your data.

Open `products/schemas.py` and define the following contracts:

```python
import uuid
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class ProductBase(BaseModel):
    """Shared attributes validated across incoming and outgoing product requests."""
    name: str = Field(..., min_length=2, max_length=120, description="Product retail name")
    price: Decimal = Field(..., ge=0.00, max_digits=10, decimal_places=2, description="Product price")
    stock: int = Field(default=0, ge=0, description="Available stock inventory")

class ProductCreate(ProductBase):
    """Schema for validating new product creation payloads."""
    pass

class ProductUpdate(BaseModel):
    """Schema for validating product update payloads (supports partial patches)."""
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

## 💰 Engineering Note: Why `Decimal`?

!!! tip "💡 Precision in Financial Data"
    In ZCore, we prefer `decimal.Decimal` over `float` for monetary values like `price`. Floating-point arithmetic can lead to rounding errors (e.g., `0.1 + 0.2` not equaling `0.3`), which is unacceptable in financial systems. Pydantic handles the conversion from JSON numbers to Python Decimals transparently.

---

## 🔗 Integration with SQLAlchemy

!!! note "🛡️ The Role of `from_attributes`"
    In Pydantic V2, setting `model_config = ConfigDict(from_attributes=True)` enables the schema to parse data directly from database models. Instead of manually mapping SQLAlchemy fields to dictionary keys, Pydantic reads properties directly from the ORM object, even when attributes are loaded lazily.

Now that our data layers (Database and Schema) are defined, we will create the **Repository Layer** to handle SQL operations for us.