# Centralized Exception Handler

Map domain-level business failures into a standardized, structured API error envelope with zero boilerplate in your route handlers.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>Error Handling</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Status</span><br>
    <strong>Security Integration</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Underlying Tech</span><br>
    <strong>FastAPI Exception Handlers</strong>
  </div>
</div>

## The Challenge

Standard FastAPI error handling often leads to inconsistent API responses:

1.  **Scattered Error Logic:** Each endpoint or service layer manually catches failures and returns ad-hoc dictionaries like `{"detail": "Not found"}` or `{"error": "Invalid data"}`, creating a fragmented API contract for frontend consumers.
2.  **Missing Diagnostic Context:** Internal details (exception type, metadata payload) are lost when converting to HTTP responses, making debugging production incidents harder.
3.  **Inconsistent HTTP Codes:** The same logical error (e.g., "entity not found") might return 404 in one endpoint, 500 in another, and 400 in a third, depending on where the exception was raised.

## The ZCore Elegance

ZCore provides a thin `AppException` hierarchy that maps directly to HTTP status codes, plus a single global handler that catches them all and formats them into the standard `ResponseWrapper` envelope. Services and repositories raise typed exceptions without any HTTP awareness.

=== "ZCore Typed Exceptions"
        :::python
        from zcore.exceptions import EntityNotFound, ValidationError, ForbiddenError

        class PaymentService(BaseService):
            async def process(self, payment_id: uuid.UUID):
                payment = await self.repository.get(payment_id)
                if not payment:
                    raise EntityNotFound("Payment record not found")
                if not payment.is_approved:
                    raise ForbiddenError("Insufficient permissions to process")
                if payment.amount <= 0:
                    raise ValidationError("Payment amount must be positive")
                return payment

        # FastAPI automatically returns:
        # 404 → {"success": false, "message": "Payment record not found", "meta": {"error_type": "EntityNotFound", "payload": null}}

=== "Standard FastAPI Error Handling"
        :::python
        from fastapi import HTTPException

        class PaymentService:
            async def process(self, payment_id: uuid.UUID):
                payment = await self.repository.get(payment_id)
                if not payment:
                    raise HTTPException(status_code=404, detail="Payment not found")
                if not payment.is_approved:
                    raise HTTPException(status_code=403, detail="Forbidden")
                if payment.amount <= 0:
                    raise HTTPException(status_code=400, detail="Invalid amount")
                return payment

        # No standard envelope across endpoints
        # No automatic error type classification in response
        # Manual HTTP code management scattered through business logic

---

## Boundaries & Integration

The exception handler is a lightweight, opt-in component registered at the application level.

*   **FastAPI Standard:** The `app_exception_handler` is a standard FastAPI exception handler registered via `app.add_exception_handler(AppException, app_exception_handler)`. It works with any FastAPI application, including those not using other ZCore components.
*   **Payload Customization:** Each exception can carry an optional `payload` dictionary. The handler includes this payload in the response `meta` object, enabling structured error details (e.g., field-level validation errors or conflict resource identifiers).
*   **Third-Party Compatibility:** Since the handler only catches `AppException` subclasses, standard Python exceptions (e.g., `ValueError`, `KeyError`) and FastAPI's built-in `HTTPException` are unaffected and handled by their default mechanisms.

---

## Under-the-Hood Spec

### 1. Status Code Mapping via Class Attribute

Each `AppException` subclass defines `status_code` as a class-level integer [exceptions/base.py]. `EntityNotFound` maps to `404`, `ValidationError` to `400`, `AuthError` to `401`, `ForbiddenError` to `403`, and `DuplicateEntity` to `409`. Custom exceptions inherit from `AppException` and can override `status_code` to any valid HTTP status.

### 2. Structured Logging Capture

The `app_exception_handler` logs every exception through `structlog` before constructing the response [exceptions/handlers.py]. The log entry includes `type`, `status_code`, `message`, `payload`, `path`, and `method`—providing a complete audit trail for debugging without exposing sensitive internals to the client.

### 3. Standard API Error Envelope

The handler constructs a `ResponseWrapper[None]` with `success=False` [exceptions/handlers.py]. The `message` field carries the human-readable error string, while `meta.error_type` stores the exact exception class name (e.g., `"EntityNotFound"`) for programmatic consumption. The `meta.payload` field is included only if the exception was raised with contextual metadata.

!!! info "Registration in main.py"
    The exception handler must be explicitly registered during application bootstrap:
    ```python
    from zcore.exceptions import AppException, app_exception_handler
    app.add_exception_handler(AppException, app_exception_handler)
    ```

!!! tip "Extending the Hierarchy"
    To add a custom error type, subclass `AppException` and set `status_code`:
    ```python
    class RateLimitExceeded(AppException):
        status_code = 429
    ```
    The existing handler automatically picks up the new type at runtime.