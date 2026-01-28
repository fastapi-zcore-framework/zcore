from abc import ABC, abstractmethod
from typing import AsyncGenerator
from fastapi import UploadFile

class StorageProvider(ABC):
    @abstractmethod
    async def upload(self, file: UploadFile, folder: str) -> str:
        """
        Uploads a file and returns the unique path/URL.
        return file path
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
        Streaming upload for large files using chunks.
        return file path
        """
        pass

    @abstractmethod
    async def delete(self, file_path: str) -> bool:
        """
        Deletes a file from storage.
        return bool result
        """
        pass