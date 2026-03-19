"""api/index.py — Vercel serverless entrypoint for mirrornode-py
Exposes the FastAPI bridge app to @vercel/python.
Routes: /, /health, /projects, /events, /events/recent, /stream, /feedback
"""
from __future__ import annotations

import json
import os
import pathlib
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="MirrorNode Bridge",
    description="MIRRORNODE distributed AI lattice — event hub & agent registry",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class MirrorNodeEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ts: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    node: str = "UNKNOWN"
    kind: str = "ANALYSIS"
    payload: Dict[str, Any] = Field(default_factory=dict)


class FeedbackPayload(BaseModel):
    agent: str
    session_id: Optional[str] = None
    rating: Optional[int] = None
    note: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# In-memory state
# ---------------------------------------------------------------------------
EVENTS: List[MirrorNodeEvent] = []
FEEDBACK: List[Dict[str, Any]] = []
CLIENTS: Set[WebSocket] = set()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _load_agents() -> List[Dict[str, Any]]:
    """Load agent definitions from bundled canon/agents directory."""
    agents_dir = pathlib.Path(__file__).parent.parent / "canon" / "agents"
    if not agents_dir.exists():
        return []
    agents = []
    for f in sorted(agents_dir.glob("*.json")):
        try:
            agents.append(json.loads(f.read_text()))
        except Exception:
            pass
    return agents


async def _broadcast(evt: MirrorNodeEvent) -> None:
    dead: list[WebSocket] = []
    for ws in CLIENTS:
        try:
            await ws.send_json(evt.model_dump())
        except Exception:
            dead.append(ws)
    for ws in dead:
        CLIENTS.discard(ws)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    return {"service": "mirrornode-bridge", "version": "0.3.0", "status": "online"}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "node": "mirrornode-backend",
        "ts": datetime.now(timezone.utc).isoformat(),
        "events": len(EVENTS),
        "clients": len(CLIENTS),
    }


@app.get("/projects")
def projects():
    agents = _load_agents()
    return {"agents": agents, "count": len(agents)}


@app.post("/events")
async def ingest_event(evt: MirrorNodeEvent):
    EVENTS.append(evt)
    await _broadcast(evt)
    return {"ok": True, "stored": evt}


@app.get("/events/recent")
def events_recent(limit: int = 20):
    limit = max(1, min(limit, 200))
    return {"ok": True, "count": min(limit, len(EVENTS)), "events": EVENTS[-limit:]}


@app.post("/feedback")
def ingest_feedback(fb: FeedbackPayload):
    record = {
        "id": str(uuid.uuid4()),
        "ts": datetime.now(timezone.utc).isoformat(),
        **fb.model_dump(),
    }
    FEEDBACK.append(record)
    return {"ok": True, "id": record["id"]}


@app.get("/feedback")
def get_feedback(limit: int = 50):
    limit = max(1, min(limit, 500))
    return {"ok": True, "count": len(FEEDBACK), "feedback": FEEDBACK[-limit:]}


@app.websocket("/stream")
async def stream(websocket: WebSocket):
    await websocket.accept()
    CLIENTS.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        CLIENTS.discard(websocket)
    except Exception:
        CLIENTS.discard(websocket)
