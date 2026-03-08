from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from .uploads_db import init_db, list_books, list_recipes_for_upload

router = APIRouter(prefix="/api/books", tags=["books"])


@router.get("")
def get_books(limit: int = Query(default=200, ge=1, le=1000)) -> dict[str, Any]:
    init_db()
    books = list_books(limit=limit)
    return {"books": books, "count": len(books)}


@router.get("/{upload_id}/recipes")
def get_book_recipes(upload_id: int) -> dict[str, Any]:
    init_db()
    books = [book for book in list_books(limit=10000) if int(book["upload_id"]) == upload_id]
    if not books:
        raise HTTPException(status_code=404, detail="Book not found.")

    recipes = list_recipes_for_upload(upload_id)
    return {"book": books[0], "recipes": recipes, "count": len(recipes)}
