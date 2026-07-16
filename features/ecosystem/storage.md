# File Storage & Security

Upload, stream, and delete files through a pluggable provider interface with multi-layer validation—extension checks, size limits, and magic byte MIME verification—all backed by path traversal protection.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>File Management</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Status</span><br>
    <strong>Optional Ecosystem</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Underlying Tech</span><br>
    <strong>aiofiles / Magic Bytes</strong>
  </div>
</div>

## The Challenge

File upload handling in web applications is a frequent source of security vulnerabilities and operational headaches:

1.  **Unrestricted File Size:** Large uploads can exhaust disk space, memory, or worker I/O, leading to Denial of Service (DoS).
2.  **Extension Masquerading:** An attacker uploads a `.png` file that contains a PHP web shell or a Windows executable. The server trusts the extension and executes the payload.
3.  **Path Traversal:** Malicious filenames like `../../etc/passwd` trick naive storage code into writing outside the designated upload directory.
4.  **Filename Collisions:** Multiple users uploading `avatar.jpg` overwrite each other's files.

## The ZCore Elegance

ZCore provides a `LocalStorageProvider` that enforces strict path bounds, generates collision-resistant filenames using truncated UUIDs, and chains configurable validators for extension, file size, and magic byte MIME verification.

=== "ZCore Secure File Upload"
        :::python
        from zcore.storage import (
            LocalStorageProvider,
            FileExtensionValidator,
            MaxFileSizeValidator,
            SafeMimeTypeValidator,
        )

        # 1. Configure layered validators
        validators = [
            FileExtensionValidator(allowed_extensions=["png", "jpg", "pdf"]),
            MaxFileSizeValidator(max_size_mb=10),
            SafeMimeTypeValidator(allowed_mimes=["image/png", "image/jpeg", "application/pdf"]),
        ]

        # 2. Create the provider
        storage = LocalStorageProvider(
            base_path="./uploads",
            validators=validators,
        )

        # 3. Upload (validated and sanitized)
        path = await storage.upload(file=uploaded_file, related_type="avatars")
        # path → "uploads/avatars/a1b2c3d4e5f6789.jpg"

=== "Standard File Upload"
        :::python
        import aiofiles
        import uuid
        from pathlib import Path

        @app.post("/upload")
        async def upload(file: UploadFile):
            # Manual validation—easy to skip or forget
            if not file.filename.endswith((".png", ".jpg")):
                raise HTTPException(400, "Invalid extension")

            # Vulnerable to path traversal
            path = f"./uploads/{file.filename}"
            
            # No size limit enforcement
            async with aiofiles.open(path, "wb") as f:
                while chunk := await file.read():
                    await f.write(chunk)

            # Filename collisions overwrite existing files

---

## Validation Pipeline

<p align="center">
  <img src="https://raw.githubusercontent.com/fastapi-zcore-framework/zcore/master/docs/assets/storage.png" 
  alt="Validation Pipeline" width="700">
</p>


---

## Boundaries & Integration

The storage layer is designed for flexibility across deployment environments.

*   **Pluggable Providers:** The abstract `StorageProvider` base class defines the contract (`upload`, `upload_stream`, `delete`). `LocalStorageProvider` is the built-in implementation, but you can write custom providers for AWS S3, Google Cloud Storage, or any other backend by subclassing `StorageProvider`.
*   **IoC Integration:** `get_storage_provider` is a FastAPI dependency that resolves the active `StorageProvider` from ZCore's DI container. This allows you to swap storage backends without changing endpoint code.
*   **Validator Composability:** Validators are standalone classes implementing `BaseStorageValidator`. They are passed as a list to `LocalStorageProvider`, which iterates them in order. Any validator raising `ValidationError` aborts the upload before any disk I/O occurs.

---

## Under-the-Hood Spec

### 1. MaxFileSizeValidator Enforcement

The `MaxFileSizeValidator` converts the configured megabyte threshold to raw bytes (`max_size_mb * 1024 * 1024`) [storage/validators.py]. It reads the file size from Starlette's native `UploadFile.size` attribute when available. For chunked multipart streams where `size` is `None`, it falls back to seeking to the end of the underlying `SpooledTemporaryFile` (`file.file.seek(0, 2)`) and reading the position, then rewinding to the start for the actual read.

### 2. SafeMimeTypeValidator Magic Bytes Verification

The validator reads the first 2048 bytes of the file payload [storage/validators.py]. It compares these header bytes against a hard-coded set of digital signatures (`SIGNATURES`) mapping magic byte sequences to MIME types (e.g., `b"\x89PNG\r\n\x1a\n"` maps to `"image/png"`). If no signature matches, it falls back to `mimetypes.guess_type`. The validator also explicitly blocks high-risk patterns:
- **PHP:** `b"<?php"`
- **HTML scripts:** `b"<script"`
- **Windows executables:** `b"MZ"`
- **Unix scripts:** `b"#!/"`
Any match triggers a critical log entry and raises `ValidationError`.

### 3. UUID Truncation for Filename Collision Resistance

The `generate_path` method in `LocalStorageProvider` generates a new filename by taking the first 15 characters of `uuid.uuid4()` [storage/local.py]. This provides 2^60 possible values—sufficient to prevent collisions in practice—while keeping filenames short and readable. The original file extension is preserved after the truncated UUID.

### 4. Path Traversal Prevention via Resolved Path Bounds

Before writing, `generate_path` resolves the `base_path` to an absolute path using `await Path(self.base_path).resolve(strict=False)` [storage/local.py]. It then constructs the target path by joining the resolved base with the normalized `related_type` subfolder. If the target path is not `is_relative_to(base)`, an `AppException("Path traversal attempt detected")` is raised and the upload is aborted.

### 5. Async Streaming with Chunked Writes

The `upload` method reads the file in 1 MB chunks (`1024 * 1024` bytes) [storage/local.py]. This prevents loading the entire file into memory, which is critical for large uploads. The `upload_stream` variant accepts an `AsyncGenerator[bytes, None]`, enabling direct binary streaming from external sources or proxy servers without intermediate buffering.

!!! info "Storage Validator Order"
    Validators execute in list order. It is recommended to place the cheapest checks first (extension) before the more expensive ones (magic bytes). This ensures fast rejection of obviously invalid uploads.

!!! tip "Custom Storage Providers"
    To implement a custom provider, subclass `StorageProvider` and implement the three abstract methods. Register the instance in the IoC container, and `get_storage_provider` will resolve it automatically for all routes:
    ```python
    container.register(StorageProvider, instance=S3StorageProvider(bucket="my-bucket"))
    ```
