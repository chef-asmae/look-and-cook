from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile

from .pdf_processing import extract_pdf_text, extract_recipes_from_pdf, save_extracted_text
from .uploads_db import create_recipe_records, create_upload_record, init_db, list_upload_records

router = APIRouter(prefix="/api/uploads", tags=["uploads"])
UPLOAD_DIR = Path("D:/data")
TEXT_OUTPUT_DIR = UPLOAD_DIR / "extracted_text"


@router.get("")
def list_uploads() -> dict[str, Any]:
    init_db()
    records = list_upload_records()
    files = [Path(record["file_path"]).name for record in records]
    return {"upload_dir": str(UPLOAD_DIR), "files": files, "records": records}


@router.post("")
async def upload_files(
    files: list[UploadFile] = File(...),
) -> dict[str, Any]:
    if not files:
        raise HTTPException(status_code=400, detail="No files were provided.")

    init_db()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    saved_files: list[dict[str, Any]] = []

    for upload in files:
        original_name = Path(upload.filename or "upload").name
        safe_name = f"{uuid4().hex}_{original_name}"
        destination = UPLOAD_DIR / safe_name
        mime_type = upload.content_type or ""

        size_bytes = 0
        with destination.open("wb") as output_file:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                output_file.write(chunk)
                size_bytes += len(chunk)

        uploaded_at = datetime.now(timezone.utc).isoformat()
        extracted_text_path = ""
        notes = "Skipped recipe analysis: file is not a PDF."
        recipes: list[dict[str, Any]] = []

        if destination.suffix.lower() == ".pdf":
            try:
                extracted_text = extract_pdf_text(destination)
                extracted_text_path = save_extracted_text(
                    TEXT_OUTPUT_DIR / f"{destination.stem}.txt",
                    extracted_text,
                )
                recipes = extract_recipes_from_pdf(destination)
                if recipes:
                    notes = f"Recipe analysis complete: {len(recipes)} recipe(s) detected."
                else:
                    notes = "Recipe analysis complete: no recipe-like sections found."
            except Exception as exc:
                notes = f"PDF parsing failed: {exc}"

        upload_id = create_upload_record(
            file_path=str(destination),
            uploaded_at=uploaded_at,
            size_bytes=size_bytes,
            mime_type=mime_type,
            recipe_count=len(recipes),
            extracted_text_path=extracted_text_path,
            notes=notes,
        )
        if recipes:
            create_recipe_records(upload_id, uploaded_at, recipes)

        saved_files.append(
            {
                "upload_id": upload_id,
                "original_name": original_name,
                "stored_name": safe_name,
                "file_path": str(destination),
                "uploaded_at": uploaded_at,
                "size_bytes": size_bytes,
                "mime_type": mime_type,
                "recipe_count": len(recipes),
                "recipes": recipes,
                "extracted_text_path": extracted_text_path,
                "notes": notes,
            }
        )
        await upload.close()

    return {"upload_dir": str(UPLOAD_DIR), "files": saved_files}
