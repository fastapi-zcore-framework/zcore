# System Utilities

Low-level data transformation, secure JSON serialization, and dynamic schema validation utilities.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>Utility Layer</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Status</span><br>
    <strong>Core Infrastructure</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Underlying Tech</span><br>
    <strong>json / jsonschema / re</strong>
  </div>
</div>

## The Challenge
Modern web applications frequently handle non-primitive data types (UUIDs, Decimals, Datetime objects) that the standard Python `json` library cannot serialize by default. Developers often resort to manual string casting or scattered `isoformat()` calls. 

Additionally, validating dynamic JSON payloads against schemas often requires repetitive `try-except` blocks to catch `jsonschema` errors and translate them into user-friendly API responses, leading to "Utility Spaghetti" across the codebase.

## The ZCore Elegance
ZCore provides a robust set of helpers to standardize data handling. The `CustomJSONEncoder` automatically handles all architectural types, while `json_dumps` and `json_loads` provide a safe, high-level interface. The `validate_json_schema` utility integrates directly with ZCore’s exception system, translating structural violations into standardized `ValidationError` responses.

=== "ZCore Utility Handling"
        :::python
        from zcore.utils.helpers import json_dumps, slugify
        from zcore.utils.json_schema import validate_json_schema

        # 1. Automatic serialization of complex types
        data = {"id": uuid.uuid4(), "price": Decimal("19.99"), "at": datetime.utcnow()}
        raw_json = json_dumps(data)

        # 2. Dynamic Schema Validation with auto-error mapping
        schema = {"type": "object", "required": ["name"]}
        validate_json_schema({"age": 25}, schema) # Raises AppException(400)

        # 3. Standardized URL slugs
        url_slug = slugify("ZCore: Modern Framework!") # "zcore-modern-framework"

=== "Raw Python Implementation"
        :::python
        # Manual conversion for standard json library
        import json

        data = {"id": uuid.uuid4(), "at": datetime.utcnow()}
        
        # Standard json.dumps(data) fails with TypeError
        raw_json = json.dumps(data, default=lambda o: str(o) if isinstance(o, uuid.UUID) else o.isoformat())

        # Manual jsonschema validation
        from jsonschema import validate, ValidationError as JSValidationError
        try:
            validate(instance=payload, schema=schema)
        except JSValidationError as e:
            # Manual translation to FastAPI responses
            raise HTTPException(status_code=400, detail=str(e))

---

## Boundaries & Integration
ZCore Utilities are built as thin, non-intrusive wrappers over standard libraries.

*   **Pydantic Integration:** While Pydantic handles its own serialization, ZCore's utilities are essential for low-level caching (Redis), logging, and WebSockets where raw Pydantic objects are not present [utils/helpers.py].
*   **Draft-7 Standards:** The `validate_json_schema` utility follows the JSON Schema Draft-7 meta-schema, ensuring industry-standard compatibility [utils/json_schema.py].
*   **Bypass:** You can continue to use Python's native `json` or `re` modules at any time. ZCore does not override global built-ins; it provides explicit alternatives for framework-specific needs.

---

## Under-the-Hood Spec

### 1. The Custom Serialization Pipeline
The `CustomJSONEncoder` implements a fallback mechanism [utils/helpers.py]. It prioritizes high-performance checks for `uuid.UUID`, `Decimal`, and `datetime/date/time` objects. If a type is still unrecognized, it performs a final `str()` cast to ensure the `json_dumps` operation never raises a `TypeError`, which is critical for logging reliability.

### 2. Schema Meta-Validation
When `validate_json_schema` is called with only one argument, it performs **Meta-Validation** [utils/json_schema.py]. It uses `Draft7Validator.check_schema(data)` to verify that the provided dictionary is itself a structurally valid JSON Schema. This is used internally by the framework to validate dynamically generated schemas before they are served or processed.

### 3. Sanitized Slugification
The `slugify` utility uses a multi-pass regex strategy [utils/helpers.py]:
1.  Removes non-alphanumeric characters.
2.  Normalizes spaces and underscores into single dashes.
3.  Trims leading/trailing dashes.
This ensures that generated slugs are always URL-safe and conform to SEO best practices without manual character mapping.

!!! info "Performance Note"
    ZCore's `json_loads` and `json_dumps` pass through additional `**kwargs` to the underlying `json` module, allowing you to use optimizations like `separators` or `sort_keys` while still benefiting from ZCore's enhanced type support.