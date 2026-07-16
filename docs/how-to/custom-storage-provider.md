# Cloud Asset Orchestration

Implement enterprise-grade cloud storage while maintaining local security defaults and rigorous file validation.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>Storage Protocol</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Status</span><br>
    <strong>Optional Provider</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Underlying Tech</span><br>
    <strong>anyio / aiofiles / Magic Bytes</strong>
  </div>
</div>

## The Challenge
Handling file uploads in FastAPI is deceptively simple until production requirements hit. Developers usually face:
1.  **Provider Lock-in:** Code written for `shutil.copyfileobj` (local disk) breaks when moving to AWS S3 or Google Cloud Storage.
2.  **Insecure Extensions:** Relying on `file.content_type` is dangerous, as attackers can easily spoof MIME types by renaming an executable to `.jpg`.
3.  **Path Traversal:** Unsanitized filenames allowing attackers to overwrite critical system files via `../../etc/passwd` exploits.
4.  **Resource Exhaustion:** Large file uploads filling up server RAM or local disk space without pre-emptive size validation.

## The ZCore Elegance
ZCore abstracts storage through the `StorageProvider` protocol. You can swap between `LocalStorageProvider` and a custom cloud provider (like S3) globally by changing a single DI registration. Every provider benefits from ZCore's multi-layered security validators, which verify file headers (Magic Bytes) and enforce strict path isolation.

=== "ZCore S3 Provider Implementation"
        :::python
        from zcore.storage import StorageProvider
        from fastapi import UploadFile

        class S3StorageProvider(StorageProvider):
            def __init__(self, bucket: str, client: Any):
                self.bucket = bucket
                self.client = client

            async def upload(self, file: UploadFile, folder: str) -> str:
                # Custom S3 logic
                path = f"{folder}/{file.filename}"
                await self.client.put_object(Bucket=self.bucket, Key=path, Body=await file.read())
                return path

        # In main.py: Global swap
        container.register_singleton(StorageProvider, S3StorageProvider(bucket="my-assets", client=s3))

=== "FastAPI Manual Upload"
        :::python
        # Logic is hardcoded to one storage type
        @app.post("/upload")
        async def upload_file(file: UploadFile):
            # 1. Manual Path Traversal Check
            if ".." in file.filename: raise HTTPException(400)
            
            # 2. Manual Size Check
            # (Requires reading part of the file or trusting headers)
            
            # 3. Hardcoded Storage Logic
            with open(f"uploads/{file.filename}", "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Moving to S3 requires rewriting this entire function.

---

## Security Validation Layer
ZCore provides a suite of modular validators that run *before* the file reaches your storage target.

```python
from zcore.storage import MaxFileSizeValidator, SafeMimeTypeValidator

# Configure local storage with strict security
storage = LocalStorageProvider(
    base_path="./uploads",
    validators=[
        MaxFileSizeValidator(max_size_mb=5),
        SafeMimeTypeValidator(allowed_mimes=["image/png", "image/jpeg", "application/pdf"])
    ]
)
```

---

## Boundaries & Integration
The storage layer is a decoupled utility that respects FastAPI's standard types.

*   **FastAPI `UploadFile`:** The `upload` method accepts the standard Starlette/FastAPI `UploadFile` object, ensuring compatibility with native multipart form handling.
*   **Dependency Injection:** Use `get_storage_provider` as a FastAPI dependency to resolve the active provider in any route, regardless of whether it is local or cloud-based.
*   **AnyIO Integration:** The `LocalStorageProvider` uses `anyio.Path` and `aiofiles` for non-blocking I/O, ensuring that file operations do not freeze the main event loop.

---

## Under-the-Hood Spec

### 1. Magic Byte Content Verification
The `SafeMimeTypeValidator` does not trust the file extension or the browser-supplied `content_type` [storage/validators.py]. It reads the first **2048 bytes** of the file and compares them against hardcoded "Magic Byte" signatures (e.g., `\x89PNG\r\n\x1a\n`). It also performs a specific security check to block high-risk patterns like `<?php`, `<script`, or Unix shebangs (`#!`) even if they appear in supposedly "safe" files.

### 2. Recursive Path Traversal Protection
The `LocalStorageProvider` uses `Path.resolve()` to normalize destination paths [storage/local.py]. Before saving, it utilizes `is_relative_to(base_path)` to verify that the final path (after resolving all `../` segments) still resides within the configured root directory. If an exploit is detected, it raises a `SecurityException` and halts the write.

### 3. Non-Blocking Stream Support
In addition to standard uploads, the interface supports `upload_stream` [storage/base.py]. This allows for direct binary streaming from asynchronous sources (like WebSockets or other external APIs) directly into storage, minimizing memory footprint for very large files.

!!! info "Security Protocol"
    By default, the `LocalStorageProvider` truncates filenames to a randomized 15-character UUID prefix [storage/local.py]. This prevents filename collisions and obscures the original file structure from end-users.