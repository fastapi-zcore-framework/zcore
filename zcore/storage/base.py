from abc import ABC, abstractmethod
from typing import AsyncGenerator
from fastapi import UploadFile

from zcore.kernel.di import Inject

class StorageProvider(ABC):
    @abstractmethod
    async def upload(self, file: UploadFile, folder: str) -> str:
        """
        Uploads a file to the storage provider.
        Returns the safe relative/absolute path of the stored file.
        """
        pass

    @abstractmethod
    async def upload_stream(
        self, 
        file_stream: AsyncGenerator[bytes, None], 
        filename: str, 
        folder: str
    ) -> str:
        """
        Streams binary data chunks directly to the storage provider.
        Returns the safe path of the stored file.
        """
        pass

    @abstractmethod
    async def delete(self, file_path: str) -> bool:
        """
        Deletes a file from the storage provider securely.
        Returns True if successful, False otherwise.
        """
        pass

async def get_storage_provider(
    provider: StorageProvider = Inject(StorageProvider)
) -> StorageProvider:
    """FastAPI Dependency stub that dynamically resolves the active StorageProvider from ZCore's IoC container."""
    return provider