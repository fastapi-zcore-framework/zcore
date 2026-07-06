from io import BytesIO
from typing import AsyncGenerator
import pytest
from fastapi import UploadFile

from zcore.exceptions.base import AppException, ValidationError
from zcore.storage.local import LocalStorageProvider
from zcore.storage.validators import MaxFileSizeValidator, SafeMimeTypeValidator

def create_mock_upload_file(content: bytes, filename: str, size: int | None = None) -> UploadFile:
    file_obj = BytesIO(content)
    upload_file = UploadFile(file=file_obj, filename=filename)
    if size is not None:
        upload_file.size = size
    else:
        if hasattr(upload_file, "size"):
            delattr(upload_file, "size")
    return upload_file

@pytest.mark.anyio
@pytest.mark.parametrize(
    "malicious_folder",
    [
        "../",
        "../../etc",
        "..\\..\\",
    ]
)
async def test_storage_path_traversal_prevention(test_storage_dir: str, malicious_folder: str) -> None:
    provider = LocalStorageProvider(base_path=test_storage_dir)
    file = create_mock_upload_file(b"test data", "malicious.txt")
    
    with pytest.raises(AppException) as exc_info:
        await provider.upload(file, malicious_folder)
    assert "Path traversal attempt detected" in str(exc_info.value)

    async def fake_stream() -> AsyncGenerator[bytes, None]:
        yield b"chunk"

    with pytest.raises(AppException) as exc_info:
        await provider.upload_stream(fake_stream(), "malicious.txt", malicious_folder)
    assert "Path traversal attempt detected" in str(exc_info.value)

    delete_success = await provider.delete(f"{test_storage_dir}/{malicious_folder}/target.txt")
    assert delete_success is False

@pytest.mark.parametrize(
    "content, filename, allowed_mimes, should_pass, error_message",
    [
        (b"\xff\xd8\xff\xe0\x00\x10JFIF", "image.jpg", ["image/jpeg"], True, ""),
        (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR", "image.png", ["image/jpeg"], False, "MIME-type is not allowed"),
        (b"<?php echo 'hello'; ?>", "test.jpg", ["image/jpeg"], False, "Security policy violation"),
        (b"<script>alert(1)</script>", "evil.jpg", ["image/jpeg"], False, "Security policy violation"),
        (b"MZ\x90\x00\x03\x00\x00\x00", "payload.jpg", ["image/jpeg"], False, "Security policy violation"),
        (b"#!/bin/sh\nrm -rf /", "exploit.jpg", ["image/jpeg"], False, "Security policy violation"),
    ]
)
def test_validator_mime_magic_bytes(
    content: bytes,
    filename: str,
    allowed_mimes: list[str],
    should_pass: bool,
    error_message: str
) -> None:
    validator = SafeMimeTypeValidator(allowed_mimes=allowed_mimes)
    file = create_mock_upload_file(content, filename)
    
    if should_pass:
        validator(file)
    else:
        with pytest.raises(ValidationError) as exc_info:
            validator(file)
        assert error_message in str(exc_info.value)

@pytest.mark.parametrize(
    "max_size_mb, size_property, content_len, should_pass",
    [
        (1.0, 500 * 1024, b"dummy", True),
        (1.0, 2 * 1024 * 1024, b"dummy", False),
        (1.0, None, 500 * 1024, True),
        (1.0, None, 2 * 1024 * 1024, False),
    ]
)
def test_validator_max_file_size(
    max_size_mb: float,
    size_property: int | None,
    content_len: int,
    should_pass: bool
) -> None:
    validator = MaxFileSizeValidator(max_size_mb=max_size_mb)
    content = b"x" * content_len if size_property is None else b"short"
    
    file = create_mock_upload_file(content, "test.bin", size=size_property)
    
    if should_pass:
        validator(file)
    else:
        with pytest.raises(ValidationError) as exc_info:
            validator(file)
        assert "exceeds the limit" in str(exc_info.value)