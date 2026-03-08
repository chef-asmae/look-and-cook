from __future__ import annotations

import re
from pathlib import Path
from typing import Union

from nltk.stem import PorterStemmer
from nltk.tokenize import RegexpTokenizer
from pypdf import PdfReader

stemmer = PorterStemmer()
tokenizer = RegexpTokenizer(r"[a-zA-Z']+")

INGREDIENT_HEADINGS = {"ingredients", "ingredient"}
INSTRUCTION_HEADINGS = {"directions", "instructions", "method", "preparation", "prep"}
COOKING_TERMS = {
    "bake",
    "boil",
    "broil",
    "chop",
    "cook",
    "dice",
    "fry",
    "grill",
    "knead",
    "marinate",
    "mix",
    "preheat",
    "roast",
    "saute",
    "simmer",
    "slice",
    "stir",
    "whisk",
}
COOKING_STEMS = {stemmer.stem(term) for term in COOKING_TERMS}
QUANTITY_PATTERN = re.compile(
    r"^\s*(\d+([\/.]\d+)?|\d+\s+\d+\/\d+|[¼½¾⅓⅔⅛⅜⅝⅞])\s*([a-zA-Z]+)?"
)
MAKES_PATTERN = re.compile(r"^\s*makes\b", re.IGNORECASE)
INSTRUCTION_START_PATTERN = re.compile(
    r"^(preheat|combine|mix|whisk|stir|add|place|heat|bring|cook|bake|roast|serve|fold|drizzle|pour)\b",
    re.IGNORECASE,
)
INGREDIENT_HINT_PATTERN = re.compile(
    r"\b(cup|cups|tablespoon|tablespoons|tbsp|teaspoon|teaspoons|tsp|ounce|ounces|oz|lb|lbs|gram|grams|g|ml)\b",
    re.IGNORECASE,
)


def _normalize_line(text: str) -> str:
    cleaned = text
    cleaned = cleaned.replace("â„", "/")
    cleaned = cleaned.replace("Â½", "1/2").replace("Â¼", "1/4").replace("Â¾", "3/4")
    cleaned = cleaned.replace("â…“", "1/3").replace("â…”", "2/3")
    cleaned = cleaned.replace("â…›", "1/8").replace("â…œ", "3/8").replace("â…", "5/8").replace("â…ž", "7/8")
    return re.sub(r"\s+", " ", cleaned.strip())


def _canonical_alpha(text: str) -> str:
    return re.sub(r"[^a-z]", "", text.lower())


def _is_ingredient_heading(line: str) -> bool:
    canonical = _canonical_alpha(line)
    return canonical in INGREDIENT_HEADINGS


def _is_instruction_heading(line: str) -> bool:
    canonical = _canonical_alpha(line)
    return canonical in INSTRUCTION_HEADINGS


def extract_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    chunks: list[str] = []

    for page in reader.pages:
        page_text = page.extract_text() or ""
        page_text = page_text.replace("\r", "\n")
        page_text = re.sub(r"[ \t]+\n", "\n", page_text)
        page_text = re.sub(r"\n{3,}", "\n\n", page_text)
        chunks.append(page_text.strip())

    merged = "\n\n".join(chunk for chunk in chunks if chunk)
    return merged.strip()


def save_extracted_text(destination: Path, extracted_text: str) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(extracted_text, encoding="utf-8")
    return str(destination)


def _line_has_cooking_terms(line: str) -> bool:
    words = tokenizer.tokenize(line.lower())
    stems = {stemmer.stem(word) for word in words}
    return len(stems.intersection(COOKING_STEMS)) > 0


def _looks_like_ingredient_line(line: str) -> bool:
    if QUANTITY_PATTERN.match(line):
        return True
    if INGREDIENT_HINT_PATTERN.search(line):
        return True
    return bool(re.match(r"^(pinch|juice of|zest of|few grinds|handful of)\b", line.lower()))


def _find_previous_title(lines: list[str], start_index: int) -> str:
    for idx in range(start_index - 1, -1, -1):
        line = _normalize_line(lines[idx])
        if not line:
            continue
        if len(line) > 90:
            continue
        if _is_ingredient_heading(line) or _is_instruction_heading(line):
            continue
        if line.isdigit():
            continue
        alpha_chars = re.sub(r"[^A-Za-z]", "", line)
        if len(alpha_chars) < 4:
            continue
        if len(line) < 4:
            continue
        if re.fullmatch(r"[A-Za-z]{1,3}", line):
            continue
        if MAKES_PATTERN.match(line):
            continue
        return line
    return "Untitled Recipe"


def _find_title_near_makes(lines: list[str], makes_index: int) -> str:
    for idx in range(makes_index - 1, max(-1, makes_index - 8), -1):
        line = _normalize_line(lines[idx])
        if not line:
            continue
        if len(line) > 90:
            continue
        if line.isdigit():
            continue
        if MAKES_PATTERN.match(line):
            continue
        if line.lower().startswith("rose water & orange blossoms"):
            continue
        if len(line.split()) < 2:
            continue
        if len(line.split()) > 10:
            continue
        if any(char in line for char in ".!?"):
            continue
        if re.search(r"\b(page|chapter|introduction|index)\b", line.lower()):
            continue
        alpha = re.sub(r"[^A-Za-z]", "", line)
        if len(alpha) < 4:
            continue
        if not _looks_like_title_line(line):
            continue
        return line
    return "Untitled Recipe"


def _looks_like_title_line(line: str) -> bool:
    words = re.findall(r"[A-Za-z][A-Za-z'’-]*", line)
    if len(words) < 2:
        return False
    uppercase_starts = sum(1 for word in words if word[0].isupper())
    ratio = uppercase_starts / len(words)
    return ratio >= 0.6


def _is_plausible_recipe_title(title: str) -> bool:
    if title == "Untitled Recipe":
        return False
    if len(title) > 80:
        return False
    if len(title.split()) < 2:
        return False
    if len(title.split()) > 10:
        return False
    if any(char in title for char in ".!?"):
        return False
    if re.search(r"\b(page|chapter|introduction|index)\b", title.lower()):
        return False
    if not _looks_like_title_line(title):
        return False
    return True


def _find_recipes_by_makes_pattern(lines: list[str]) -> list[dict[str, Union[str, int]]]:
    recipes: list[dict[str, Union[str, int]]] = []

    for idx, raw_line in enumerate(lines):
        line = _normalize_line(raw_line)
        if not MAKES_PATTERN.match(line):
            continue

        title = _find_title_near_makes(lines, idx)
        ingredient_count = 0
        instruction_count = 0
        preview_lines: list[str] = []

        for next_idx in range(idx + 1, min(idx + 120, len(lines))):
            candidate = _normalize_line(lines[next_idx])
            if not candidate:
                continue

            if MAKES_PATTERN.match(candidate):
                break

            if _looks_like_ingredient_line(candidate):
                ingredient_count += 1
                if len(preview_lines) < 3:
                    preview_lines.append(candidate)
                continue

            if INSTRUCTION_START_PATTERN.match(candidate) or _line_has_cooking_terms(candidate):
                instruction_count += 1
                if len(preview_lines) < 3:
                    preview_lines.append(candidate)
                if instruction_count >= 2 and ingredient_count >= 3:
                    break

        score = ingredient_count + (2 * instruction_count)
        if ingredient_count >= 3 and instruction_count >= 1:
            recipes.append(
                {
                    "title": title,
                    "score": score,
                    "preview": " | ".join(preview_lines)[:240],
                }
            )

    return recipes


def find_recipes(extracted_text: str) -> list[dict[str, Union[str, int]]]:
    if not extracted_text.strip():
        return []

    lines = extracted_text.splitlines()
    recipes: list[dict[str, Union[str, int]]] = []

    for idx, raw_line in enumerate(lines):
        line = _normalize_line(raw_line)
        if not _is_ingredient_heading(line):
            continue

        title = _find_previous_title(lines, idx)
        ingredient_count = 0
        instruction_count = 0
        cooking_signal_count = 0
        instruction_heading_seen = False
        preview_lines: list[str] = []

        for next_idx in range(idx + 1, min(idx + 80, len(lines))):
            section_line = _normalize_line(lines[next_idx])
            if not section_line:
                continue

            if _is_ingredient_heading(section_line) and next_idx > idx + 1:
                break
            if _is_instruction_heading(section_line):
                instruction_heading_seen = True
                continue

            if _looks_like_ingredient_line(section_line):
                ingredient_count += 1
            if _line_has_cooking_terms(section_line):
                cooking_signal_count += 1
                instruction_count += 1
            elif re.match(r"^\d+[\).]?\s+", section_line):
                instruction_count += 1

            if len(preview_lines) < 3:
                preview_lines.append(section_line)

        score = ingredient_count + instruction_count + cooking_signal_count + int(instruction_heading_seen)
        if ingredient_count >= 2 and (
            instruction_count >= 1 or cooking_signal_count >= 1 or instruction_heading_seen
        ):
            recipes.append(
                {
                    "title": title,
                    "score": score,
                    "preview": " | ".join(preview_lines)[:240],
                }
            )

    if not recipes:
        recipes = _find_recipes_by_makes_pattern(lines)

    deduped: dict[str, dict[str, Union[str, int]]] = {}
    for recipe in recipes:
        key = str(recipe["title"]).strip().lower()
        if key not in deduped or int(recipe["score"]) > int(deduped[key]["score"]):
            deduped[key] = recipe

    sorted_recipes = sorted(deduped.values(), key=lambda recipe: int(recipe["score"]), reverse=True)
    return sorted_recipes[:20]


def _clean_book_name(raw_name: str) -> str:
    name = re.sub(r"^[0-9a-f]{32}_", "", raw_name, flags=re.IGNORECASE)
    name = re.sub(r"\.pdf$", "", name, flags=re.IGNORECASE)
    name = name.replace("_", " ").strip()
    return name or raw_name


def _extract_recipes_from_lines(lines: list[str], page_number: int, book_name: str) -> list[dict[str, Union[str, int, list[str]]]]:
    recipes: list[dict[str, Union[str, int, list[str]]]] = []

    for idx, raw_line in enumerate(lines):
        line = _normalize_line(raw_line)
        if not MAKES_PATTERN.match(line):
            continue

        title = _find_title_near_makes(lines, idx)
        ingredient_lines: list[str] = []
        preview_lines: list[str] = []
        instruction_count = 0

        for next_idx in range(idx + 1, min(idx + 140, len(lines))):
            candidate = _normalize_line(lines[next_idx])
            if not candidate:
                continue

            if MAKES_PATTERN.match(candidate):
                break

            if _looks_like_ingredient_line(candidate):
                if candidate not in ingredient_lines:
                    ingredient_lines.append(candidate)
                if len(preview_lines) < 3:
                    preview_lines.append(candidate)
                continue

            if INSTRUCTION_START_PATTERN.match(candidate) or _line_has_cooking_terms(candidate):
                instruction_count += 1
                if len(preview_lines) < 3:
                    preview_lines.append(candidate)
                if instruction_count >= 2 and len(ingredient_lines) >= 3:
                    break

        if len(ingredient_lines) >= 3 and instruction_count >= 1 and _is_plausible_recipe_title(title):
            recipes.append(
                {
                    "title": title,
                    "book_name": book_name,
                    "page_number": page_number,
                    "ingredients": ingredient_lines[:50],
                    "preview": " | ".join(preview_lines)[:240],
                    "score": len(ingredient_lines) + (2 * instruction_count),
                }
            )

    return recipes


def extract_recipes_from_pdf(pdf_path: Path) -> list[dict[str, Union[str, int, list[str]]]]:
    reader = PdfReader(str(pdf_path))
    book_name = _clean_book_name(str(reader.metadata.title or pdf_path.name))
    recipes: list[dict[str, Union[str, int, list[str]]]] = []

    for page_index, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        lines = page_text.splitlines()
        page_recipes = _extract_recipes_from_lines(lines, page_index + 1, book_name)
        recipes.extend(page_recipes)

    deduped: dict[str, dict[str, Union[str, int, list[str]]]] = {}
    for recipe in recipes:
        key = f"{str(recipe['title']).strip().lower()}::{int(recipe['page_number'])}"
        if key not in deduped or int(recipe["score"]) > int(deduped[key]["score"]):
            deduped[key] = recipe

    return sorted(deduped.values(), key=lambda r: int(r["score"]), reverse=True)
