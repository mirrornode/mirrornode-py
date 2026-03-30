"""api/index.py — Vercel serverless entrypoint for mirrornode-py
Exposes the FastAPI bridge app to @vercel/python.
"""
from __future__ import annotations
import asyncio
import json
import os
import pathlib
import re
import uuid
from datetime import datetime, timezone, timedelta
from fastapi.responses import JSONResponsefrom enum 
import Enum
from typing import Any, Dict, List, Optional, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# --- App ---
app = FastAPI(title="MirrorNode Bridge", version="0.6.0")
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
        description="If true, simulate standby without state change",
    )

# --- State ---
EVENTS: List[MirrorNodeEvent] = []
CLIENTS: Dict[WebSocket, Dict[str, Any]] = {}  # {ws: {node_id, capabilities}}
_STANDBY: Dict[str, Dict[str, Any]] = {}  # {node: {reason, dry_run, last_updated}}
_STANDBY_LOCK = asyncio.Lock()

# --- Bastet Coherence Scoring ---
def _bastet_coherence_score(node: str, window_minutes: int = 10) -> float:
    """[@MIRROR] Eve/Bastet: compute shadow_signal density for node over window.
    Returns a 0.0-1.0 float: ratio of shadow_signal events to total events in window.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    window_events = [
        e for e in EVENTS
        if e.node == node and datetime.fromisoformat(e.ts) >= cutoff
    ]
    if not window_events:
        return 0.0
    shadow_count = sum(1 for e in window_events if e.shadow_signal)
    return round(shadow_count / len(window_events), 4)

async def _broadcast(evt: MirrorNodeEvent):
    dead = []
    for ws in CLIENTS:
        try:
            await ws.send_json(evt.model_dump())
        except:
            dead.append(ws)
    for ws in dead:
        CLIENTS.pop(ws, None)

# --- Routes ---
@app.get("/health")
def health():
    return {"status": "ok", "events": len(EVENTS), "clients": len(CLIENTS)}

@app.get("/events/recent")
def events_recent(limit: int = 20):
    # [@MIRROR] Eve/Bastet hook: annotate recent events with live coherence score
    events = EVENTS[-limit:]
    for e in events:
        if e.shadow_signal:
            e.payload["_bastet_coherence"] = _bastet_coherence_score(e.node)
    return {"ok": True, "events": events}

@app.post("/events")
async def ingest_event(evt: MirrorNodeEvent):
    EVENTS.append(evt)
    await _broadcast(evt)
    return {"ok": True}

@app.post("/standby")
async def standby(req: StandbyRequest):
    """Put a node into standby. If dry_run=True, simulate without mutating state."""
    entry = {
        "node": req.node,
        "reason": req.reason,
        "dry_run": req.dry_run,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    if req.dry_run:
        return {"ok": True, "simulated": True, "entry": entry}
    async with _STANDBY_LOCK:
        _STANDBY[req.node] = entry
    return {"ok": True, "simulated": False, "entry": entry}

@app.get("/standby/status")
def standby_status():
    """[@MIRROR] Bastet coherence v0.6.0 — standby status 
with coherence scoring."""
    try:
        ts = datetime.now(timezone.utc).isoformat()

        # Per-node coherence scores over the recent window
        node_scores = {
            node: _bastet_coherence_score(node)
            for node in _STANDBY.keys()
        }

        # Simple aggregate: max score across nodes (0.0 if 
none)
        aggregate_score = max(node_scores.values()) if 
node_scores else 0.0

        return {
            "status": "ok",
            "version": "0.6.0",
            "ts": ts,
            "standby": _STANDBY,
            "_bastet_coherence": {
                "engine": "bastet",
                "version": "0.6.0",
                "score": float(aggregate_score),
                "node_scores": node_scores,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "version": "0.6.0",
                "ts": datetime.now(timezone.utc).isoformat(),
                "standby": _STANDBY,
                "_bastet_coherence": {
                    "engine": "bastet",
                    "version": "0.6.0",
                    "score": 0.0,
                    "node_scores": {},
                },
                "error": str(e),
            },
        )
# --- Merlin Handoff ---
class MerlinHandoff(BaseModel):
    """[@MIRROR] Structured handoff payload targeting Merlin."""
    from_node: str
    payload: Dict[str, Any]
    reason: Optional[str] = None
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

@app.post("/handoff/merlin")
async def handoff_to_merlin(req: MerlinHandoff):
    """[@MIRROR] Route a structured handoff event to Merlin."""
    evt = MirrorNodeEvent(
        node="merlin",
        kind="HANDOFF",
        payload={
            "from_node": req.from_node,
            "reason": req.reason,
            "trace_id": req.trace_id,
            **req.payload,
        },
        shadow_signal=True,
    )
    EVENTS.append(evt)
    await _broadcast(evt)
    return {"ok": True, "trace_id": req.trace_id, "routed_to": "merlin"}

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
    except:
        pass
    finally:
        CLIENTS.pop(websocket, None)
