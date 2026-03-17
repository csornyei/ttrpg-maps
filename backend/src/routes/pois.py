import asyncio

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)

from src.config import Settings, get_settings
from src.models import PoiCreate, PoiDetail, PoiSummary, PoiUpdate
from src.observability import (
    websocket_connected,
    websocket_disconnected,
    websocket_message_sent,
)
from src.poi_store import poi_store
from src.security import require_write_auth

api_router = APIRouter(prefix="/api/pois", tags=["pois"])
ws_router = APIRouter(tags=["pois-ws"])


@api_router.get("")
async def list_pois() -> list[PoiSummary]:
    return poi_store.get_all_summaries()


@api_router.get("/{poi_id}")
async def get_poi(poi_id: str) -> PoiDetail:
    detail = poi_store.get_detail_by_id(poi_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="PoI not found")
    return detail


@api_router.post("", status_code=status.HTTP_201_CREATED)
async def create_poi(
    poi: PoiCreate,
    _: None = Depends(require_write_auth),
) -> PoiDetail:
    try:
        return poi_store.create_poi(poi)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@api_router.put("/{poi_id}")
async def update_poi(
    poi_id: str,
    poi: PoiUpdate,
    _: None = Depends(require_write_auth),
) -> PoiDetail:
    detail = poi_store.update_poi(poi_id, poi)
    if detail is None:
        raise HTTPException(status_code=404, detail="PoI not found")
    return detail


@api_router.delete("/{poi_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_poi(
    poi_id: str,
    _: None = Depends(require_write_auth),
) -> Response:
    deleted = poi_store.delete_poi(poi_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="PoI not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@ws_router.websocket("/ws/pois")
async def pois_ws(
    websocket: WebSocket, settings: Settings = Depends(get_settings)
) -> None:
    await websocket.accept()
    websocket_connected()
    try:
        while True:
            summaries = poi_store.get_all_summaries()
            await websocket.send_json([summary.model_dump() for summary in summaries])
            websocket_message_sent()
            await asyncio.sleep(settings.update_interval_seconds)
            poi_store.advance_moving_pois()
    except WebSocketDisconnect:
        pass
    finally:
        websocket_disconnected()
