from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Union
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile

from .uploads_db import create_upload_record, init_db, list_upload_records

router = APIRouter(prefix="/api/uploads", tags=["uploads"])
UPLOAD_DIR = Path("D:/data")


@router.get("")
def list_uploads() -> dict[str, Union[list[str], list[dict[str, Union[str, int]]], str]]:
    init_db()
    records = list_upload_records()
    files = [Path(record["file_path"]).name for record in records]
    return {"upload_dir": str(UPLOAD_DIR), "files": files, "records": records}


@router.post("")
async def upload_files(
    files: list[UploadFile] = File(...),
) -> dict[str, Union[list[dict[str, Union[str, int]]], str]]:
    if not files:
        raise HTTPException(status_code=400, detail="No files were provided.")

    init_db()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    saved_files: list[dict[str, Union[str, int]]] = []

    for upload in files:
        original_name = Path(upload.filename or "upload.bin").name
        safe_name = f"{uuid4().hex}_{original_name}"
        destination = UPLOAD_DIR / safe_name

        size_bytes = 0
        with destination.open("wb") as output_file:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                output_file.write(chunk)
                size_bytes += len(chunk)

        uploaded_at = datetime.now(timezone.utc).isoformat()
        create_upload_record(str(destination), uploaded_at, size_bytes)

        saved_files.append(
            {
                "original_name": original_name,
                "stored_name": safe_name,
                "file_path": str(destination),
                "uploaded_at": uploaded_at,
                "size_bytes": size_bytes,
            }
        )
        await upload.close()

    return {"upload_dir": str(UPLOAD_DIR), "files": saved_files}
