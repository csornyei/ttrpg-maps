from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from src.observability import record_frontend_load

FRONTEND_DIST_DIR = Path(__file__).resolve().parent.parent / "static"
FRONTEND_INDEX_FILE = FRONTEND_DIST_DIR / "index.html"

router = APIRouter(include_in_schema=False)


@router.get("/")
async def serve_root() -> FileResponse:
    if FRONTEND_INDEX_FILE.is_file():
        record_frontend_load()
        return FileResponse(FRONTEND_INDEX_FILE)
    raise HTTPException(status_code=404, detail="Frontend bundle not found")


@router.get("/{full_path:path}")
async def serve_spa(full_path: str) -> FileResponse:
    if full_path.startswith(("api/", "ws/")):
        raise HTTPException(status_code=404, detail="Not found")

    requested_file = FRONTEND_DIST_DIR / full_path
    if requested_file.is_file():
        return FileResponse(requested_file)

    if FRONTEND_INDEX_FILE.is_file():
        record_frontend_load()
        return FileResponse(FRONTEND_INDEX_FILE)

    raise HTTPException(status_code=404, detail="Frontend bundle not found")
