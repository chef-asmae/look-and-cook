from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile

from .upload_service import list_uploads_payload, process_upload

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


@router.get("")
def list_uploads() -> dict[str, Any]:
    return list_uploads_payload()


@router.post("")
async def upload_files(files: list[UploadFile] = File(...)) -> dict[str, Any]:
    if not files:
        raise HTTPException(status_code=400, detail="No files were provided.")

    saved_files: list[dict[str, Any]] = []
    for upload in files:
        saved_files.append(await process_upload(upload))
        await upload.close()

    return {"files": saved_files}
