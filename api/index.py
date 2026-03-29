"""api/index.py — Vercel serverless entrypoint for mirrornode-py
Exposes the FastAPI bridge app to @vercel/python.
"""
from __future__ import annotations
import json
import os
import pathlib
import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# --- App ---
app = FastAPI(title="MirrorNode Bridge", version="0.5.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# --- Models ---
class MirrorNodeEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ts: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    node: str = "UNKNOWN"
    kind: str = "ANALYSIS"
    payload: Dict[str, Any] = Field(default_factory=dict)
    shadow_signal: bool = False  # [@MIRROR] Eve/Bastet: intuitive pattern flag

class HermesEnvelope(BaseModel):
    """Hermes Message Schema v1."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ts: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    from_node: str
    to_node: str
    kind: str
    payload: Dict[str, Any]
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
class StandbyRequest(BaseModel):
    node: str
    reason: Optional[str] = None
    dry_run: bool = Field(
        default=False,
        description="If true, simulate standby without state 
change",
    )
# --- State ---
EVENTS: List[MirrorNodeEvent] = []
CLIENTS: Dict[WebSocket, Dict[str, Any]] = {} # {ws: {node_id, capabilities}}

async def _broadcast(evt: MirrorNodeEvent):
    dead = []
    for ws in CLIENTS:
        try:
            await ws.send_json(evt.model_dump())
        except: dead.append(ws)
    for ws in dead: CLIENTS.pop(ws, None)

@app.get("/health")
def health():
    return {"status": "ok", "events": len(EVENTS), "clients": len(CLIENTS)}

@app.get("/events/recent")
def events_recent(limit: int = 20):
    # [@MIRROR] Eve/Bastet hook: annotate recent events with coherence
    events = EVENTS[-limit:]
    for e in events:
        if e.shadow_signal:
            e.payload["_bastet_coherence"] = 0.42 # Example annotation
    return {"ok": True, "events": events}

@app.post("/events")
async def ingest_event(evt: MirrorNodeEvent):
    EVENTS.append(evt)
    await _broadcast(evt)
    return {"ok": True}

@app.websocket("/stream")
async def stream(websocket: WebSocket):
    await websocket.accept()
    try:
        # Hermes Handshake
        init_data = await websocket.receive_json()
        CLIENTS[websocket] = {
            "node_id": init_data.get("node_id", "anonymous"),
            "capabilities": init_data.get("capabilities", [])
        }
        while True:
            await websocket.receive_text()
    except: pass
    finally: CLIENTS.pop(websocket, None)
