from __future__ import annotations

import sqlite3
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
                size_bytes INTEGER NOT NULL
            )
            """
        )
        connection.commit()


def create_upload_record(file_path: str, uploaded_at: str, size_bytes: int) -> None:
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO uploads (file_path, uploaded_at, size_bytes)
            VALUES (?, ?, ?)
            """,
            (file_path, uploaded_at, size_bytes),
        )
        connection.commit()


def list_upload_records() -> list[dict[str, Union[str, int]]]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT id, file_path, uploaded_at, size_bytes
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
        }
        for row in rows
    ]
