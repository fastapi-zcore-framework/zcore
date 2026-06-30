import uuid
import structlog
from pathlib import Path as SyncPath
from typing import AsyncGenerator
from anyio import Path as AsyncPath
import aiofiles
from fastapi import UploadFile

from zcore.storage.base import StorageProvider
from zcore.exceptions.base import AppException

logger = structlog.get_logger()

class LocalStorageProvider(StorageProvider):
    def __init__(self, base_path: str) -> None:
        self.base_path = base_path

    async def generate_path(self, filename: str, related_type: str) -> str:
        base = SyncPath(self.base_path).resolve(strict=False)
        target_folder = (SyncPath(self.base_path) / related_type).resolve(strict=False)
        
        if not target_folder.is_relative_to(base):
            raise AppException("Path traversal attempt detected")
        
        uuid_file_name = str(uuid.uuid4())[:15]
        ext = SyncPath(filename).suffix
        if any(char in ext for char in ["/", "\\", "..", "\x00"]):
            ext = ".bin"
            
        new_file_name = f"{uuid_file_name}{ext}"
        final_path = target_folder / new_file_name
        
        async_folder = AsyncPath(target_folder)
        if not await async_folder.exists():
            await async_folder.mkdir(parents=True, exist_ok=True)
        
        return str(final_path)

    async def upload(self, file: UploadFile, related_type: str) -> str:
        try:
            path = await self.generate_path(file.filename or "file", related_type)
            async with aiofiles.open(path, "wb") as buffer:
                while chunk := await file.read(1024 * 1024):
                    await buffer.write(chunk)
        except AppException as e:
            raise e
        except Exception as e:
            logger.error("Failed to upload file to local storage due to system error")
            raise AppException("Error saving file")
        return path

    async def upload_stream(
        self, 
        file_stream: AsyncGenerator[bytes, None], 
        filename: str, 
        related_type: str
    ) -> str:
        try:
            path = await self.generate_path(filename, related_type)
            async with aiofiles.open(path, "wb") as buffer:
                async for chunk in file_stream:
                    await buffer.write(chunk)
        except AppException as e:
            raise e
        except Exception as e:
            logger.error("Failed to stream upload file to local storage due to system error")
            raise AppException("Error saving file")
        return path

    async def delete(self, file_path: str) -> bool:
        try:
            base = SyncPath(self.base_path).resolve(strict=False)
            path_to_delete = SyncPath(file_path).resolve(strict=False)
            if not path_to_delete.is_relative_to(base):
                logger.warning(f"Prevented arbitrary file deletion attempt outside base path: {file_path}")
                return False
            
            async_path = AsyncPath(path_to_delete)
            await async_path.unlink(missing_ok=True)
            return True
        except Exception as e:
            logger.error(f"Failed to delete file: {file_path}")
            return False