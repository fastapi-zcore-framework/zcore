# 📁 How-To: Implementing a Custom S3 Storage Provider

## ❓ The Problem

By default, ZCore includes a `LocalStorageProvider` that saves uploaded files directly to the host machine's filesystem. While this works well for development, production environments often require storing files in cloud storage solutions like AWS S3 or MinIO to support scalability and high availability.

To switch storage backends, you need a way to swap the storage provider globally without modifying your application's route handlers or service logic.

---

## 🛠️ The ZCore Solution

We suggest creating a custom storage class that inherits from ZCore's abstract `StorageProvider` base class and registering it in the IoC container during application bootstrapping.

```mermaid
graph LR
    Client[Client Upload Request] --> Router[API Router / Service]
    Router -->|Resolves interface| SP[StorageProvider interface]
    
    subgraph IoC Container Injection
        SP -->|Injected Singleton| S3[S3StorageProvider Class]
    end
    
    S3 -->|Asynchronously upload| Target[AWS S3 Bucket / MinIO]
```

---

### 📦 Step 1: Implement the Custom S3 Storage Provider

Create a custom storage provider that implements the abstract `upload`, `upload_stream`, and `delete` methods. 

We use the asynchronous `aioboto3` library to perform non-blocking uploads:

```python
import structlog
from typing import AsyncGenerator
from fastapi import UploadFile
import aioboto3

from zcore.storage.base import StorageProvider
from zcore.exceptions.base import AppException

logger = structlog.get_logger()

class S3StorageProvider(StorageProvider):
    """Custom cloud storage integration mapping ZCore operations to AWS S3 / MinIO."""

    def __init__(
        self, 
        aws_access_key_id: str, 
        aws_secret_access_key: str, 
        bucket_name: str,
        region_name: str = "us-east-1",
        endpoint_url: str | None = None # Use for custom targets like MinIO
    ) -> None:
        self.session = aioboto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name
        )
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url

    async def upload(self, file: UploadFile, folder: str) -> str:
        """Upload an API file to the configured S3 bucket."""
        target_path = f"{folder}/{file.filename}"
        
        try:
            async with self.session.client("s3", endpoint_url=self.endpoint_url) as s3:
                # Read file payload
                file_data = await file.read()
                
                await s3.put_object(
                    Bucket=self.bucket_name,
                    Key=target_path,
                    Body=file_data,
                    ContentType=file.content_type
                )
            logger.info(f"Successfully uploaded file to S3: s3://{self.bucket_name}/{target_path}")
            return target_path
        except Exception as e:
            logger.error(f"Failed to upload file to S3: {e}")
            raise AppException("Error uploading file to cloud storage.")

    async def upload_stream(
        self, 
        file_stream: AsyncGenerator[bytes, None], 
        filename: str, 
        folder: str
    ) -> str:
        """Stream file bytes directly to S3."""
        target_path = f"{folder}/{filename}"
        
        try:
            async with self.session.client("s3", endpoint_url=self.endpoint_url) as s3:
                # To support multipart streaming in S3
                mpu = await s3.create_multipart_upload(Bucket=self.bucket_name, Key=target_path)
                parts = []
                part_number = 1
                
                async for chunk in file_stream:
                    part = await s3.upload_part(
                        Bucket=self.bucket_name,
                        Key=target_path,
                        PartNumber=part_number,
                        UploadId=mpu["UploadId"],
                        Body=chunk
                    )
                    parts.append({"PartNumber": part_number, "ETag": part["ETag"]})
                    part_number += 1
                
                await s3.complete_multipart_upload(
                    Bucket=self.bucket_name,
                    Key=target_path,
                    UploadId=mpu["UploadId"],
                    MultipartUpload={"Parts": parts}
                )
            return target_path
        except Exception as e:
            logger.error(f"S3 streaming upload failed: {e}")
            raise AppException("Error streaming file payload to cloud storage.")

    async def delete(self, file_path: str) -> bool:
        """Remove a file from the S3 bucket."""
        try:
            async with self.session.client("s3", endpoint_url=self.endpoint_url) as s3:
                await s3.delete_object(Bucket=self.bucket_name, Key=file_path)
            return True
        except Exception as e:
            logger.error(f"Failed to delete S3 asset: {e}")
            return False
```

---

### ⚙️ Step 2: Register the Provider in the IoC Container

To configure your application to use the S3 provider, register it as a global singleton in the IoC container during application bootstrapping:

```python
# main.py
from zcore.kernel.di import container
from zcore.storage.base import StorageProvider
from zcore.config import settings
from .storage import S3StorageProvider

# Instantiate the custom S3 provider
s3_provider = S3StorageProvider(
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    bucket_name=settings.AWS_BUCKET_NAME,
    endpoint_url=settings.AWS_S3_ENDPOINT_URL # Optional: configure for MinIO
)

# Register the provider as a singleton in the IoC container
container.register_singleton(StorageProvider, s3_provider)
```

---

### 🚦 Step 3: Usage in Your Application

Because your services resolve the storage provider through the IoC container, you can use S3 storage throughout your application without changing your business logic:

```python
from fastapi import APIRouter, UploadFile, Depends
from zcore.storage.base import StorageProvider, get_storage_provider

router = APIRouter(prefix="/assets")

@router.post("/upload")
async def upload_user_avatar(
    file: UploadFile,
    storage: StorageProvider = Depends(get_storage_provider)
):
    # This automatically uses S3StorageProvider and returns the S3 path
    saved_path = await storage.upload(file, folder="avatars")
    return {"path": saved_path}
```

---

## 💡 Engineering Insights

!!! tip "💡 Decoupled Scalability"
    By abstracting S3 operations behind the `StorageProvider` interface, you can easily swap storage providers (e.g., switching from S3 to local storage for local testing) simply by changing the container's registered singleton.