from __future__ import annotations

import re
from pathlib import Path
from typing import Union

from pypdf import PdfReader

from .recipe_extractor import clean_book_name, extract_recipes_from_lines


def extract_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    chunks: list[str] = []

    for page in reader.pages:
        page_text = page.extract_text() or ""
        page_text = page_text.replace("\r", "\n")
        page_text = re.sub(r"[ \t]+\n", "\n", page_text)
        page_text = re.sub(r"\n{3,}", "\n\n", page_text)
        chunks.append(page_text.strip())

    return "\n\n".join(chunk for chunk in chunks if chunk).strip()


def extract_pdf_metadata(pdf_path: Path) -> dict[str, str]:
    reader = PdfReader(str(pdf_path))
    metadata = reader.metadata or {}
    raw_title = str(getattr(metadata, "title", "") or "")
    raw_author = str(getattr(metadata, "author", "") or "")
    title = clean_book_name(raw_title or pdf_path.name)
    author = raw_author.strip()
    return {"title": title, "author": author}


def extract_recipes_from_pdf(pdf_path: Path) -> list[dict[str, Union[str, int, list[str]]]]:
    reader = PdfReader(str(pdf_path))
    book_name = clean_book_name(str(reader.metadata.title or pdf_path.name))
    recipes: list[dict[str, Union[str, int, list[str]]]] = []

    for page_index, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        page_recipes = extract_recipes_from_lines(page_text.splitlines(), page_index + 1, book_name)
        recipes.extend(page_recipes)

    deduped: dict[str, dict[str, Union[str, int, list[str]]]] = {}
    for recipe in recipes:
        key = f"{str(recipe['title']).strip().lower()}::{int(recipe['page_number'])}"
        if key not in deduped or int(recipe["score"]) > int(deduped[key]["score"]):
            deduped[key] = recipe

    return sorted(deduped.values(), key=lambda r: int(r["score"]), reverse=True)
