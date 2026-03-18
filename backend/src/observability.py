import logging

from fastapi import APIRouter, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, generate_latest

HTTP_RESPONSES_TOTAL = Counter(
    "daggerheart_http_responses_total",
    "Total HTTP responses labeled by method, route path template, and status code",
    ["method", "path", "status_code"],
)

FRONTEND_LOADS_TOTAL = Counter(
    "daggerheart_frontend_loads_total",
    "Total number of frontend index loads",
)

WS_ACTIVE_CONNECTIONS = Gauge(
    "daggerheart_ws_active_connections",
    "Current number of active websocket connections",
)

WS_MESSAGES_TOTAL = Counter(
    "daggerheart_ws_messages_total",
    "Total websocket messages sent",
)

metrics_router = APIRouter(include_in_schema=False)


def setup_logging(log_level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def _route_path_label(request: Request) -> str:
    route = request.scope.get("route")
    if route is not None and getattr(route, "path", None):
        return str(route.path)
    return request.url.path


def record_http_response(request: Request, status_code: int) -> None:
    HTTP_RESPONSES_TOTAL.labels(
        method=request.method,
        path=_route_path_label(request),
        status_code=str(status_code),
    ).inc()


def record_frontend_load() -> None:
    FRONTEND_LOADS_TOTAL.inc()


def websocket_connected() -> None:
    WS_ACTIVE_CONNECTIONS.inc()


def websocket_disconnected() -> None:
    WS_ACTIVE_CONNECTIONS.dec()


def websocket_message_sent() -> None:
    WS_MESSAGES_TOTAL.inc()


@metrics_router.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


logger = logging.getLogger("daggerheart.api")
