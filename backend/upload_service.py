from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from .epub_parser import extract_epub_metadata, extract_epub_text, extract_recipes_from_epub
from .pdf_parser import extract_pdf_metadata, extract_pdf_text, extract_recipes_from_pdf
from .upload_fs import UPLOAD_DIR, ensure_upload_dir, save_extracted_text, save_uploaded_file
from .uploads_db import delete_recipe_records, create_recipe_records, init_db, list_upload_records, upsert_upload_record


def list_uploads_payload() -> dict[str, Any]:
    init_db()
    records = list_upload_records()
    files = [Path(record["file_path"]).name for record in records]
    return {"upload_dir": str(UPLOAD_DIR), "files": files, "records": records}


async def process_upload(upload: UploadFile) -> dict[str, Any]:
    init_db()
    ensure_upload_dir()

    original_name, file_hash, destination, size_bytes, already_exists = await save_uploaded_file(upload)
    mime_type = upload.content_type or ""
    uploaded_at = datetime.now(timezone.utc).isoformat()
    extracted_text_path = ""
    notes = "Skipped recipe analysis: unsupported file type."
    recipes: list[dict[str, Any]] = []
    book_title = Path(original_name).stem
    book_author = ""

    suffix = destination.suffix.lower()
    if suffix in {".pdf", ".epub"}:
        try:
            if suffix == ".pdf":
                metadata = extract_pdf_metadata(destination)
                book_title = metadata.get("title") or book_title
                book_author = metadata.get("author") or ""
                extracted_text = extract_pdf_text(destination)
                recipes = extract_recipes_from_pdf(destination)
            else:
                metadata = extract_epub_metadata(destination)
                book_title = metadata.get("title") or book_title
                book_author = metadata.get("author") or ""
                extracted_text = extract_epub_text(destination)
                recipes = extract_recipes_from_epub(destination)

            extracted_text_path = save_extracted_text(file_hash, extracted_text)
            if recipes:
                notes = f"Recipe analysis complete: {len(recipes)} recipe(s) detected."
            else:
                notes = "Recipe analysis complete: no recipe-like sections found."
        except Exception as exc:
            notes = f"{suffix.upper()[1:]} parsing failed: {exc}"

    upload_id, was_reprocessed = upsert_upload_record(
        file_hash=file_hash,
        file_path=str(destination),
        book_title=book_title,
        book_author=book_author,
        uploaded_at=uploaded_at,
        size_bytes=size_bytes,
        mime_type=mime_type,
        recipe_count=len(recipes),
        extracted_text_path=extracted_text_path,
        notes=notes,
    )
    if was_reprocessed:
        notes = f"{notes} Reprocessed existing file hash."
        upload_id, _ = upsert_upload_record(
            file_hash=file_hash,
            file_path=str(destination),
            book_title=book_title,
            book_author=book_author,
            uploaded_at=uploaded_at,
            size_bytes=size_bytes,
            mime_type=mime_type,
            recipe_count=len(recipes),
            extracted_text_path=extracted_text_path,
            notes=notes,
        )
    delete_recipe_records(upload_id)
    if recipes:
        create_recipe_records(upload_id, uploaded_at, recipes)

    return {
        "upload_id": upload_id,
        "original_name": original_name,
        "stored_name": destination.name,
        "file_hash": file_hash,
        "was_reprocessed": was_reprocessed,
        "file_path": str(destination),
        "book_title": book_title,
        "book_author": book_author,
        "uploaded_at": uploaded_at,
        "size_bytes": size_bytes,
        "mime_type": mime_type,
        "recipe_count": len(recipes),
        "recipes": recipes,
        "extracted_text_path": extracted_text_path,
        "notes": notes,
    }
