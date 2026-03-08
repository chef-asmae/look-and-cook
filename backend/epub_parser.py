from __future__ import annotations

import re
import zipfile
from html import unescape
from pathlib import Path
from typing import Union
from xml.etree import ElementTree as ET

from .recipe_extractor import clean_book_name, extract_recipes_from_lines


def _strip_markup(html_text: str) -> str:
    text = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", html_text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _epub_reading_order(epub_path: Path) -> tuple[list[str], str, str]:
    with zipfile.ZipFile(epub_path, "r") as archive:
        container_xml = archive.read("META-INF/container.xml")
        container_root = ET.fromstring(container_xml)
        rootfile = container_root.find(".//{*}rootfile")
        if rootfile is None:
            return [], clean_book_name(epub_path.name), ""

        opf_path = rootfile.attrib.get("full-path", "")
        if not opf_path:
            return [], clean_book_name(epub_path.name), ""

        opf_dir = Path(opf_path).parent.as_posix()
        opf_root = ET.fromstring(archive.read(opf_path))

        title_element = opf_root.find(".//{*}metadata/{*}title")
        creator_element = opf_root.find(".//{*}metadata/{*}creator")
        book_name = clean_book_name(title_element.text or epub_path.name) if title_element is not None else clean_book_name(epub_path.name)
        book_author = (creator_element.text or "").strip() if creator_element is not None else ""

        manifest_items: dict[str, str] = {}
        for item in opf_root.findall(".//{*}manifest/{*}item"):
            item_id = item.attrib.get("id")
            href = item.attrib.get("href", "")
            if not item_id or not href:
                continue
            full_path = f"{opf_dir}/{href}" if opf_dir else href
            manifest_items[item_id] = Path(full_path).as_posix()

        ordered_paths: list[str] = []
        for itemref in opf_root.findall(".//{*}spine/{*}itemref"):
            idref = itemref.attrib.get("idref")
            if not idref:
                continue
            path = manifest_items.get(idref)
            if path:
                ordered_paths.append(path)

    return ordered_paths, book_name, book_author


def extract_epub_text(epub_path: Path) -> str:
    ordered_paths, _, _ = _epub_reading_order(epub_path)
    chunks: list[str] = []

    with zipfile.ZipFile(epub_path, "r") as archive:
        for item_path in ordered_paths:
            try:
                raw = archive.read(item_path).decode("utf-8", errors="ignore")
            except KeyError:
                continue
            chunk = _strip_markup(raw)
            if chunk:
                chunks.append(chunk)

    return "\n\n".join(chunks).strip()


def extract_recipes_from_epub(epub_path: Path) -> list[dict[str, Union[str, int, list[str]]]]:
    ordered_paths, book_name, _ = _epub_reading_order(epub_path)
    recipes: list[dict[str, Union[str, int, list[str]]]] = []

    with zipfile.ZipFile(epub_path, "r") as archive:
        for chapter_index, item_path in enumerate(ordered_paths, start=1):
            try:
                raw = archive.read(item_path).decode("utf-8", errors="ignore")
            except KeyError:
                continue

            chapter_text = _strip_markup(raw)
            if not chapter_text:
                continue

            chapter_recipes = extract_recipes_from_lines(chapter_text.splitlines(), chapter_index, book_name)
            recipes.extend(chapter_recipes)

    deduped: dict[str, dict[str, Union[str, int, list[str]]]] = {}
    for recipe in recipes:
        key = f"{str(recipe['title']).strip().lower()}::{int(recipe['page_number'])}"
        if key not in deduped or int(recipe["score"]) > int(deduped[key]["score"]):
            deduped[key] = recipe

    return sorted(deduped.values(), key=lambda r: int(r["score"]), reverse=True)


def extract_epub_metadata(epub_path: Path) -> dict[str, str]:
    _, book_name, book_author = _epub_reading_order(epub_path)
    return {"title": book_name, "author": book_author}
