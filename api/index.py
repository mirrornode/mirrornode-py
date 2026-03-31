from __future__ import annotations
import time
import os
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ========================
# App Setup
# ========================
app = FastAPI(title="MirrorNode Bridge", version="0.6.0")

# Record startup time for uptime calculations
app.startup_time = time.time()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========================
# Models
# ========================
class MirrorNodeEvent(BaseModel):
    id: str = Field(default_factory=lambda: 
str(uuid.uuid4()))
    ts: str = Field(default_factory=lambda: 
datetime.now(timezone.utc).isoformat())
    node: str = "UNKNOWN"
    kind: str = "ANALYSIS"
    payload: Dict[str, Any] = Field(default_factory=dict)
    shadow_signal: bool = False


class StandbyRequest(BaseModel):
    node: str
    reason: Optional[str] = None
    dry_run: bool = False


class MerlinHandoff(BaseModel):
    """[@MIRROR] Structured handoff payload targeting 
Merlin."""
    from_node: str
    payload: Dict[str, Any]
    reason: Optional[str] = None
    trace_id: str = Field(default_factory=lambda: 
str(uuid.uuid4()))


# ========================
# Module-Level State (Shared Across Warm Instances)
# ========================
EVENTS: List[MirrorNodeEvent] = []
CLIENTS: Dict[WebSocket, Dict[str, Any]] = {}
_STANDBY: Dict[str, Dict[str, Any]] = {}
_STANDBY_LOCK = asyncio.Lock()


# ========================
# Bastet Coherence Engine v0.6.0
# ========================
def _bastet_coherence_score(node: str, window_minutes: int = 
10) -> float:
    """Calculate Bastet coherence score based on recent 
shadow signals."""
    cutoff = datetime.now(timezone.utc) - 
timedelta(minutes=window_minutes)
    
    window_events = [
        e for e in EVENTS
        if e.node == node and datetime.fromisoformat(e.ts) >= 
cutoff
    ]
    
    if not window_events:
        return 0.0
    
    shadow_count = sum(1 for e in window_events if 
e.shadow_signal)
    return round(shadow_count / len(window_events), 4)


# ========================
# Broadcast Helper
# ========================
async def _broadcast(evt: MirrorNodeEvent):
    dead = []
    for ws in list(CLIENTS.keys()):
        try:
            await ws.send_json(evt.model_dump())
        except Exception:
            dead.append(ws)
    
    for ws in dead:
        CLIENTS.pop(ws, None)


# ========================
# Routes
# ========================

@app.get("/health")
def health():
    return {
        "status": "ok",
        "events": len(EVENTS),
        "clients": len(CLIENTS),
    }


@app.post("/events")
async def ingest_event(evt: MirrorNodeEvent):
    EVENTS.append(evt)
    await _broadcast(evt)
    return {"ok": True}


@app.post("/standby")
async def standby(req: StandbyRequest):
    entry = {
        "node": req.node,
        "reason": req.reason,
        "dry_run": req.dry_run,
        "last_updated": 
datetime.now(timezone.utc).isoformat(),
    }
    
    if req.dry_run:
        return {"ok": True, "simulated": True, "entry": 
entry}
    
    async with _STANDBY_LOCK:
        _STANDBY[req.node] = entry
    
    return {"ok": True, "simulated": False, "entry": entry}


@app.get("/standby/status")
async def get_standby_status():
    """RISING_STAR + Bastet v0.6.0 combined endpoint"""
    try:
        now = datetime.now(timezone.utc).isoformat()
        uptime_s = int(time.time() - getattr(app, 
'startup_time', time.time()))

        # Calculate coherence across all standby nodes
        node_scores = {
            node: _bastet_coherence_score(node)
            for node in _STANDBY.keys()
        }
        aggregate_score = max(node_scores.values()) if 
node_scores else 0.0

        return {
            "protocol": "RISING_STAR",
            "version": "1.1.0",
            "environment": os.getenv("MIRRORNODE_ENV", 
"prod"),
            "status": "ONLINE",
            "uptime_s": uptime_s,
            "ts": now,
            "standby": _STANDBY,
            "_bastet_coherence": {
                "engine": "bastet",
                "version": "0.6.0",
                "score": float(aggregate_score),
                "node_scores": node_scores,
                "event_count": len(EVENTS),
                "signal_density": len(EVENTS) / max(1, 
len(EVENTS) + 20)
            }
        }
    except Exception as e:
        # Safe fallback - never break the endpoint
        now = datetime.now(timezone.utc).isoformat()
        return JSONResponse(
            status_code=200,  # Keep it 200 even on internal 
error
            content={
                "protocol": "RISING_STAR",
                "version": "1.1.0",
                "status": "DEGRADED",
                "ts": now,
                "standby": _STANDBY,
                "_bastet_coherence": {
                    "engine": "bastet",
                    "version": "0.6.0",
                    "score": 0.0,
                    "node_scores": {},
                    "event_count": len(EVENTS),
                    "error": str(e)[:200]
                }
            }
        )


@app.post("/handoff/merlin")
async def handoff_to_merlin(req: MerlinHandoff):
    """[@MIRROR] Route a structured handoff event to 
Merlin."""
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
    return {"ok": True, "trace_id": req.trace_id, 
"routed_to": "merlin"}


@app.websocket("/stream")
async def stream(websocket: WebSocket):
    await websocket.accept()
    CLIENTS[websocket] = {"node_id": "anonymous"}
    
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        CLIENTS.pop(websocket, None)


# ========================
# Vercel Serverless Entrypoint
# ========================
handler = app
