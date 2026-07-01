import mimetypes
import structlog
from typing import List, Set, Union, Optional
from fastapi import UploadFile
from zcore.exceptions.base import ValidationError

logger = structlog.get_logger()

# Hardened digital signatures of popular safe formats (Magic Bytes)
SIGNATURES = {
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
    b"%PDF": "application/pdf",
    b"RIFF": "image/webp",
}

class BaseStorageValidator:
    def __call__(self, file: UploadFile) -> None:
        raise NotImplementedError

class FileExtensionValidator(BaseStorageValidator):
    def __init__(self, allowed_extensions: Union[List[str], Set[str]], message: Optional[str] = None):
        self.allowed_extensions = {
            ext.lower() if ext.startswith(".") else f".{ext.lower()}" 
            for ext in allowed_extensions
        }
        self.message = message or f"File extension not allowed. Allowed extensions are: {', '.join(sorted(self.allowed_extensions))}"

    def __call__(self, file: UploadFile) -> None:
        filename = file.filename or ""
        ext = f".{filename.split('.')[-1].lower()}" if "." in filename else ""
        
        if ext not in self.allowed_extensions:
            raise ValidationError(message=self.message)

class MaxFileSizeValidator(BaseStorageValidator):
    """
    Enforces a maximum file size limit (configured in MegaBytes) 
    to protect the host machine from DoS and storage-exhaustion attacks.
    """
    def __init__(self, max_size_mb: float, message: Optional[str] = None):
        self.max_size_bytes = int(max_size_mb * 1024 * 1024)
        self.max_size_mb = max_size_mb
        self.message = message or f"File size exceeds the limit of {max_size_mb} MB."

    def __call__(self, file: UploadFile) -> None:
        # Utilize Starlette's native file.size if populated, fallback to seek evaluation
        size = getattr(file, "size", None)
        
        if size is None:
            try:
                # Fallback seeking for chunked multipart parsers
                file.file.seek(0, 2)
                size = file.file.tell()
                file.file.seek(0)
            except Exception as e:
                logger.error(f"Failed to dynamically evaluate file size: {e}")
                raise ValidationError(message="Failed to process file size validation.")

        if size > self.max_size_bytes:
            raise ValidationError(message=self.message)

class SafeMimeTypeValidator(BaseStorageValidator):
    """
    Checks the first 2048 bytes of the binary payload to verify that
    declared extensions match the physical header signatures of safe file formats.
    """
    def __init__(self, allowed_mimes: Union[List[str], Set[str]], message: Optional[str] = None):
        self.allowed_mimes = set(allowed_mimes)
        self.message = message or "Uploaded file content is corrupted or its MIME-type is not allowed."

    def __call__(self, file: UploadFile) -> None:
        try:
            header_bytes = file.file.read(2048)
            file.file.seek(0)
        except Exception as e:
            logger.error(f"Failed to read magic bytes for verification: {e}")
            raise ValidationError(message="Failed to validate file signatures.")

        # Blocks PHP block tags, HTML script tags, Unix shebang scripts and Windows Executables
        if b"<?php" in header_bytes or b"<script" in header_bytes or header_bytes.startswith(b"MZ") or header_bytes.startswith(b"#!/"):
            logger.critical(f"BLOCKED EXECUTE INJECTION ATTEMPT. Malicious file signature in filename: '{file.filename}'")
            raise ValidationError(message="Security policy violation: Executable scripts are strictly blocked.")

        detected_mime = None
        for signature, mime in SIGNATURES.items():
            if header_bytes.startswith(signature):
                detected_mime = mime
                break

        # Fallback to standard Python guessing if signature is not mapped (e.g. for safe text files)
        if not detected_mime and file.filename:
            detected_mime, _ = mimetypes.guess_type(file.filename)

        if not detected_mime or detected_mime not in self.allowed_mimes:
            logger.warning(f"File validation failed. Detected MIME '{detected_mime}' not in allowed list.")
            raise ValidationError(message=self.message)