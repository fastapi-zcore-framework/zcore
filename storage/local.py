import uuid
from anyio import Path 
import aiofiles

from typing import Annotated
from fastapi import Depends

from app.core.config import settings

from app.core.storage.base import StorageProvider
from app.core.exceptions import AppException

CHUNK_SIZE = 1024 * 1024

class LocalStorageProvider(StorageProvider):
    async def generate_path(self, filename, related_type):
        folder = settings.STORAGE_PATH
        uuid_file_name = str(uuid.uuid4())[:15]
        
        ext = Path(filename).suffix 
        new_file_name = f"{uuid_file_name}{ext}"
        
        folder_path = Path(folder) / related_type
        
        if not await folder_path.exists():
            await folder_path.mkdir(parents=True, exist_ok=True)
        
        return str(folder_path / new_file_name)
    
    async def upload(self, file, related_type):
        try:
            path = await self.generate_path(file.filename, related_type)
            async with aiofiles.open(path, "wb",) as buffer :
                await buffer.write(await file.read())
        except Exception as e:
            raise AppException("Error saving file")
        
        return path
    
    async def upload_stream(self, file_stream, filename, related_type):
        try:
            path = await self.generate_path(filename, related_type)
            async with aiofiles.open(path, "wb") as buffer :
                async for _ in file_stream:
                    await buffer.write(_)
        except Exception as e:
            raise AppException("Error saving file")       
        return path
    
    async def delete(self, file_path):
        path = Path(file_path)
        try:
            await path.unlink(missing_ok=True)
            return True
        except Exception:
            return False
        
StorageProviderDep = Annotated[LocalStorageProvider, Depends()]