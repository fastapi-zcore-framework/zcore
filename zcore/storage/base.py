from abc import ABC, abstractmethod
from typing import AsyncGenerator
from fastapi import UploadFile

class StorageProvider(ABC):
    @abstractmethod
    async def upload(self, file: UploadFile, folder: str) -> str:
        pass

    @abstractmethod
    async def upload_stream(
        self, 
        file_stream: AsyncGenerator[bytes, None], 
        filename: str, 
        folder: str
    ) -> str:
        pass

    @abstractmethod
    async def delete(self, file_path: str) -> bool:
        pass

async def get_storage_provider() -> StorageProvider:
    raise NotImplementedError("StorageProvider dependency override is required")