from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Set
import uuid

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.mount("/hud", StaticFiles(directory="hud/websocket", html=True), 
name="hud")


class MirrorNodeEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ts: str = Field(default_factory=lambda: 
datetime.now(timezone.utc).isoformat())
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


@app.get("/health")
def health():
    return {"ok": True, "events": len(EVENTS), "clients": len(CLIENTS)}


@app.get("/")
def root():
    return {"service": "mirrornode-bridge", "status": "online"}


@app.post("/events")
async def ingest_event(evt: MirrorNodeEvent):
    EVENTS.append(evt)
    await broadcast(evt)
    return {"ok": True, "stored": evt}


@app.get("/events/recent")
def events_recent(limit: int = 20):
    limit = max(1, min(limit, 200))
    return {"ok": True, "count": min(limit, len(EVENTS)), "events": 
EVENTS[-limit:]}


@app.websocket("/stream")
async def stream(websocket: WebSocket):
    await websocket.accept()
    CLIENTS.add(websocket)
    try:
        while True:
            # Client can send any text as keepalive; server ignores it.
            await websocket.receive_text()
    except WebSocketDisconnect:
        CLIENTS.discard(websocket)
    except Exception:
        CLIENTS.discard(websocket)

