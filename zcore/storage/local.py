import uuid
from typing import AsyncGenerator
from anyio import Path
import aiofiles
from fastapi import UploadFile

from zcore.storage.base import StorageProvider
from zcore.exceptions.base import AppException

class LocalStorageProvider(StorageProvider):
    def __init__(self, base_path: str) -> None:
        self.base_path = base_path

    async def generate_path(self, filename: str, related_type: str) -> str:
        uuid_file_name = str(uuid.uuid4())[:15]
        ext = Path(filename).suffix
        new_file_name = f"{uuid_file_name}{ext}"
        folder_path = Path(self.base_path) / related_type
        
        if not await folder_path.exists():
            await folder_path.mkdir(parents=True, exist_ok=True)
        
        return str(folder_path / new_file_name)

    async def upload(self, file: UploadFile, related_type: str) -> str:
        try:
            path = await self.generate_path(file.filename or "file", related_type)
            async with aiofiles.open(path, "wb") as buffer:
                while chunk := await file.read(1024 * 1024):
                    await buffer.write(chunk)
        except Exception:
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
        except Exception:
            raise AppException("Error saving file")
        return path

    async def delete(self, file_path: str) -> bool:
        path = Path(file_path)
        try:
            await path.unlink(missing_ok=True)
            return True
        except Exception:
            return False