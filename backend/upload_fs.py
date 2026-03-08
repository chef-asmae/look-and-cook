from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

UPLOAD_DIR = Path("D:/data")
TEXT_OUTPUT_DIR = UPLOAD_DIR / "extracted_text"


def ensure_upload_dir() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


async def save_uploaded_file(upload: UploadFile) -> tuple[str, str, Path, int, bool]:
    original_name = Path(upload.filename or "upload").name
    extension = Path(original_name).suffix.lower() or ".bin"
    temp_path = UPLOAD_DIR / f"{uuid4().hex}.tmp"

    hasher = hashlib.sha256()
    size_bytes = 0
    with temp_path.open("wb") as output_file:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            output_file.write(chunk)
            hasher.update(chunk)
            size_bytes += len(chunk)

    file_hash = hasher.hexdigest()
    destination = UPLOAD_DIR / f"{file_hash}{extension}"
    already_exists = destination.exists()

    if already_exists:
        temp_path.unlink(missing_ok=True)
    else:
        temp_path.replace(destination)

    return original_name, file_hash, destination, size_bytes, already_exists


def save_extracted_text(file_hash: str, extracted_text: str) -> str:
    destination = TEXT_OUTPUT_DIR / f"{file_hash}.txt"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(extracted_text, encoding="utf-8")
    return str(destination)
