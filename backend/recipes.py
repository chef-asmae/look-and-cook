from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from .uploads_db import get_recipe_by_id, init_db, search_recipes

router = APIRouter(prefix="/api/recipes", tags=["recipes"])


@router.get("")
def list_recipes(
    q: str = Query(default="", max_length=200),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    init_db()
    recipes = search_recipes(query=q, limit=limit)
    return {"recipes": recipes, "query": q, "count": len(recipes)}


@router.get("/{recipe_id}")
def get_recipe(recipe_id: int) -> dict[str, Any]:
    init_db()
    recipe = get_recipe_by_id(recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found.")
    return {"recipe": recipe}
