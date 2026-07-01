import uuid
import structlog
from typing import AsyncGenerator, List, Optional
from anyio import Path
import aiofiles
from fastapi import UploadFile

from zcore.storage.base import StorageProvider
from zcore.storage.validators import BaseStorageValidator
from zcore.exceptions.base import AppException

logger = structlog.get_logger()

class LocalStorageProvider(StorageProvider):
    def __init__(
        self, 
        base_path: str, 
        validators: Optional[List[BaseStorageValidator]] = None
    ) -> None:
        self.base_path = base_path
        self.validators = validators or []

    async def generate_path(self, filename: str, related_type: str) -> str:
        base = await Path(self.base_path).resolve(strict=False)
        target_folder = await (Path(self.base_path) / related_type).resolve(strict=False)
        
        if not target_folder.is_relative_to(base):
            raise AppException("Path traversal attempt detected")
        
        uuid_file_name = str(uuid.uuid4())[:15]
        ext = Path(filename).suffix.lower()
        
        new_file_name = f"{uuid_file_name}{ext}"
        final_path = target_folder / new_file_name
        
        if not await target_folder.exists():
            await target_folder.mkdir(parents=True, exist_ok=True)
        
        return final_path.as_posix()

    def _validate_file(self, file: UploadFile) -> None:
        """Runs the upload file through the registered validators pipeline sequentially."""
        for validator in self.validators:
            validator(file)

    async def upload(self, file: UploadFile, related_type: str) -> str:
        self._validate_file(file)
        
        try:
            path = await self.generate_path(file.filename or "file", related_type)
            async with aiofiles.open(path, "wb") as buffer:
                while chunk := await file.read(1024 * 1024):
                    await buffer.write(chunk)
        except AppException as e:
            raise e
        except Exception as e:
            logger.error(f"Failed to upload file to local storage due to system error: {e}")
            raise AppException("Error saving file")
        return path

    async def upload_stream(
        self, 
        file_stream: AsyncGenerator[bytes, None], 
        filename: str, 
        related_type: str
    ) -> str:
        # Path trajectory safeguards are strictly maintained during stream path generation.
        try:
            path = await self.generate_path(filename, related_type)
            async with aiofiles.open(path, "wb") as buffer:
                async for chunk in file_stream:
                    await buffer.write(chunk)
        except AppException as e:
            raise e
        except Exception as e:
            logger.error(f"Failed to stream upload file to local storage due to system error: {e}")
            raise AppException("Error saving file")
        return path

    async def delete(self, file_path: str) -> bool:
        try:
            base = await Path(self.base_path).resolve(strict=False)
            path_to_delete = await Path(file_path).resolve(strict=False)
            
            # Directory Traversal Safeguard on deletion too
            if not path_to_delete.is_relative_to(base):
                logger.warning(f"Prevented arbitrary file deletion attempt outside base path: {file_path}")
                return False
            
            await path_to_delete.unlink(missing_ok=True)
            return True
        except Exception as e:
            logger.error(f"Failed to delete file: {file_path}. Error: {e}")
            return False