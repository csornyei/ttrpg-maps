from pathlib import Path
from time import perf_counter

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.config import get_settings
from src.observability import metrics_router, record_http_response, setup_logging
from src.routes.frontend import router as frontend_router
from src.routes.health import router as health_router
from src.routes.pois import api_router as pois_api_router
from src.routes.pois import ws_router as pois_ws_router

settings = get_settings()
setup_logging(settings.log_level)
logger = logging.getLogger("daggerheart.api")

app = FastAPI()

allowed_origins = ["*"] if settings.env == "dev" else [settings.frontend_origin]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_observability(request, call_next):
    started_at = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (perf_counter() - started_at) * 1000
        record_http_response(request, 500)
        logger.exception("Request failed %s %s duration_ms=%.2f", request.method, request.url.path, duration_ms)
        raise

    duration_ms = (perf_counter() - started_at) * 1000
    record_http_response(request, response.status_code)
    logger.info(
        "Request completed %s %s status=%s duration_ms=%.2f",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response

FRONTEND_DIST_DIR = Path(__file__).resolve().parent / "static"
app.include_router(pois_api_router)
app.include_router(pois_ws_router)
app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(frontend_router)


if (FRONTEND_DIST_DIR / "assets").is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_DIST_DIR / "assets"),
        name="assets",
    )
