from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Set
import uuid
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Response
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from .metrics import (
    events_total,
    events_stored,
    websocket_clients,
    http_request_duration
)

app = FastAPI()
app.mount("/hud", StaticFiles(directory="hud/websocket", html=True), name="hud")


class MirrorNodeEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ts: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    node: str = "UNKNOWN"
    kind: str = "ANALYSIS"
    payload: Dict[str, Any] = Field(default_factory=dict)


EVENTS: List[MirrorNodeEvent] = []
CLIENTS: Set[WebSocket] = set()


async def broadcast(evt: MirrorNodeEvent) -> None:
    dead: list[WebSocket] = []
    for ws in CLIENTS:
        try:
            await ws.send_json(evt.model_dump())
        except Exception:
            dead.append(ws)
    for ws in dead:
        CLIENTS.discard(ws)
        websocket_clients.dec()


@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
def health():
    start = time.time()
    result = {"ok": True, "events": len(EVENTS), "clients": len(CLIENTS)}
    http_request_duration.labels(method="GET", endpoint="/health").observe(time.time() - start)
    return result


@app.get("/")
def root():
    return {"service": "mirrornode-bridge", "status": "online"}


@app.post("/events")
async def ingest_event(evt: MirrorNodeEvent):
    start = time.time()
    EVENTS.append(evt)
    events_total.labels(node=evt.node, kind=evt.kind).inc()
    events_stored.set(len(EVENTS))
    await broadcast(evt)
    http_request_duration.labels(method="POST", endpoint="/events").observe(time.time() - start)
    return {"ok": True, "stored": evt}


@app.get("/events/recent")
def events_recent(limit: int = 20):
    start = time.time()
    limit = max(1, min(limit, 200))
    result = {"ok": True, "count": min(limit, len(EVENTS)), "events": EVENTS[-limit:]}
    http_request_duration.labels(method="GET", endpoint="/events/recent").observe(time.time() - start)
    return result


@app.websocket("/stream")
async def stream(websocket: WebSocket):
    await websocket.accept()
    CLIENTS.add(websocket)
    websocket_clients.set(len(CLIENTS))
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        CLIENTS.discard(websocket)
        websocket_clients.set(len(CLIENTS))
    except Exception:
        CLIENTS.discard(websocket)
        websocket_clients.set(len(CLIENTS))
