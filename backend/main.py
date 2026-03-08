from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .recipes import router as recipes_router
from .uploads import router as uploads_router
from .uploads_db import init_db

app = FastAPI(title="FastAPI + React Backend")
DIST_DIR = Path(__file__).parent.parent / "frontend" / "dist"
ASSETS_DIR = DIST_DIR / "assets"

# Allow local React development servers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/hello")
def hello() -> dict[str, str]:
    return {"message": "Hello from FastAPI"}


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(uploads_router)
app.include_router(recipes_router)


@app.on_event("startup")
def startup() -> None:
    init_db()


app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR), check_dir=False), name="assets")


@app.get("/{full_path:path}")
def serve_react_app(full_path: str):
    requested_file = DIST_DIR / full_path if full_path else DIST_DIR / "index.html"

    if full_path and requested_file.is_file():
        return FileResponse(requested_file)

    index_file = DIST_DIR / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)

    return JSONResponse(
        status_code=503,
        content={"error": "React build not found. Run `npm run build` in `frontend`."},
    )
