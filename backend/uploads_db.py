from __future__ import annotations

import sqlite3
from json import dumps, loads
from pathlib import Path
from typing import Union

UPLOAD_DIR = Path("D:/data")
DB_PATH = UPLOAD_DIR / "uploads.sqlite3"


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                mime_type TEXT NOT NULL DEFAULT '',
                recipe_count INTEGER NOT NULL DEFAULT 0,
                extracted_text_path TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT ''
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                upload_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                book_name TEXT NOT NULL,
                page_number INTEGER NOT NULL DEFAULT 0,
                ingredients_json TEXT NOT NULL DEFAULT '[]',
                preview TEXT NOT NULL DEFAULT '',
                score INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(upload_id) REFERENCES uploads(id) ON DELETE CASCADE
            )
            """
        )
        _ensure_columns(connection)
        connection.commit()


def _ensure_columns(connection: sqlite3.Connection) -> None:
    rows = connection.execute("PRAGMA table_info(uploads)").fetchall()
    existing_columns = {str(row["name"]) for row in rows}
    required_columns = {
        "mime_type": "TEXT NOT NULL DEFAULT ''",
        "recipe_count": "INTEGER NOT NULL DEFAULT 0",
        "extracted_text_path": "TEXT NOT NULL DEFAULT ''",
        "notes": "TEXT NOT NULL DEFAULT ''",
    }

    for column_name, definition in required_columns.items():
        if column_name not in existing_columns:
            connection.execute(f"ALTER TABLE uploads ADD COLUMN {column_name} {definition}")


def create_upload_record(
    file_path: str,
    uploaded_at: str,
    size_bytes: int,
    mime_type: str,
    recipe_count: int,
    extracted_text_path: str,
    notes: str,
) -> int:
    with _connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO uploads (
                file_path,
                uploaded_at,
                size_bytes,
                mime_type,
                recipe_count,
                extracted_text_path,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (file_path, uploaded_at, size_bytes, mime_type, recipe_count, extracted_text_path, notes),
        )
        connection.commit()
        return int(cursor.lastrowid)


def create_recipe_records(upload_id: int, created_at: str, recipes: list[dict[str, Union[str, int, list[str]]]]) -> None:
    if not recipes:
        return

    with _connect() as connection:
        connection.executemany(
            """
            INSERT INTO recipes (
                upload_id,
                title,
                book_name,
                page_number,
                ingredients_json,
                preview,
                score,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    upload_id,
                    str(recipe.get("title", "Untitled Recipe")),
                    str(recipe.get("book_name", "")),
                    int(recipe.get("page_number", 0)),
                    dumps(recipe.get("ingredients", []), ensure_ascii=False),
                    str(recipe.get("preview", "")),
                    int(recipe.get("score", 0)),
                    created_at,
                )
                for recipe in recipes
            ],
        )
        connection.commit()


def list_upload_records() -> list[dict[str, Union[str, int]]]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT id, file_path, uploaded_at, size_bytes, mime_type, recipe_count, extracted_text_path, notes
            FROM uploads
            ORDER BY id DESC
            """
        ).fetchall()

    return [
        {
            "id": int(row["id"]),
            "file_path": str(row["file_path"]),
            "uploaded_at": str(row["uploaded_at"]),
            "size_bytes": int(row["size_bytes"]),
            "mime_type": str(row["mime_type"] or ""),
            "recipe_count": int(row["recipe_count"] or 0),
            "extracted_text_path": str(row["extracted_text_path"] or ""),
            "notes": str(row["notes"] or ""),
        }
        for row in rows
    ]


def search_recipes(query: str = "", limit: int = 100) -> list[dict[str, Union[str, int]]]:
    with _connect() as connection:
        if query.strip():
            wildcard = f"%{query.strip().lower()}%"
            rows = connection.execute(
                """
                SELECT id, upload_id, title, book_name, page_number, preview, score, created_at
                FROM recipes
                WHERE lower(title) LIKE ? OR lower(book_name) LIKE ? OR lower(preview) LIKE ?
                ORDER BY score DESC, id DESC
                LIMIT ?
                """,
                (wildcard, wildcard, wildcard, limit),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT id, upload_id, title, book_name, page_number, preview, score, created_at
                FROM recipes
                ORDER BY score DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    return [
        {
            "id": int(row["id"]),
            "upload_id": int(row["upload_id"]),
            "title": str(row["title"]),
            "book_name": str(row["book_name"]),
            "page_number": int(row["page_number"]),
            "preview": str(row["preview"]),
            "score": int(row["score"]),
            "created_at": str(row["created_at"]),
        }
        for row in rows
    ]


def get_recipe_by_id(recipe_id: int) -> dict[str, Union[str, int, list[str]]] | None:
    with _connect() as connection:
        row = connection.execute(
            """
            SELECT id, upload_id, title, book_name, page_number, ingredients_json, preview, score, created_at
            FROM recipes
            WHERE id = ?
            """,
            (recipe_id,),
        ).fetchone()

    if row is None:
        return None

    ingredients_raw = str(row["ingredients_json"] or "[]")
    try:
        ingredients = loads(ingredients_raw)
    except Exception:
        ingredients = []

    return {
        "id": int(row["id"]),
        "upload_id": int(row["upload_id"]),
        "title": str(row["title"]),
        "book_name": str(row["book_name"]),
        "page_number": int(row["page_number"]),
        "ingredients": ingredients if isinstance(ingredients, list) else [],
        "preview": str(row["preview"]),
        "score": int(row["score"]),
        "created_at": str(row["created_at"]),
    }
