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

from core.registry.cache import get_registry, NUMERAETHE_PRIMITIVES
from core.engines.fusion import synthesize_lattice, compute_lattice_metrics, processGlyph

# ========================
# App Setup
# ========================
app = FastAPI(title="MirrorNode Bridge", version="1.1.1")

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
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ts: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    node: str = "UNKNOWN"
    kind: str = "ANALYSIS"
    payload: Dict[str, Any] = Field(default_factory=dict)
    shadow_signal: bool = False


class StandbyRequest(BaseModel):
    node: str
    reason: Optional[str] = None
    dry_run: bool = False


class MerlinHandoff(BaseModel):
    """[@MIRROR] Structured handoff payload targeting Merlin."""
    from_node: str
    payload: Dict[str, Any]
    reason: Optional[str] = None
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class SynthesizeRequest(BaseModel):
    """Request body for /api/fusion/synthesize."""
    root_ids: List[str]


# ========================
# Module-Level State (Shared Across Warm Instances)
# ========================
EVENTS: List[MirrorNodeEvent] = []
CLIENTS: Dict[WebSocket, Dict[str, Any]] = {}
_STANDBY: Dict[str, Dict[str, Any]] = {}
_STANDBY_LOCK = asyncio.Lock()

# Telemetry v2 — live symbolic metrics updated on each sync/synthesis
_SYMBOLIC_METRICS: Dict[str, Any] = {
    "symbolic_depth": 0,
    "nesting_density": 0.0,
    "total_nodes": 0,
    "terminal_nodes": 0,
    "composite_nodes": 0,
    "loops_detected": 0,
    "last_synthesis_ts": None,
}


# ========================
# Bastet Coherence Engine v0.6.0
# ========================
def _bastet_coherence_score(node: str, window_minutes: int = 10) -> float:
    """Calculate Bastet coherence score based on recent shadow signals."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    window_events = [
        e for e in EVENTS
        if e.node == node and datetime.fromisoformat(e.ts) >= cutoff
    ]
    if not window_events:
        return 0.0
    shadow_count = sum(1 for e in window_events if e.shadow_signal)
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
# Routes — Core
# ========================

@app.get("/health")
def health():
    reg = get_registry()
    return {
        "status": "ok",
        "version": "1.1.1",
        "events": len(EVENTS),
        "clients": len(CLIENTS),
        "glyph_count": reg.count(),
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
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    if req.dry_run:
        return {"ok": True, "simulated": True, "entry": entry}
    async with _STANDBY_LOCK:
        _STANDBY[req.node] = entry
    return {"ok": True, "simulated": False, "entry": entry}


@app.get("/standby/status")
async def get_standby_status():
    """RISING_STAR + Bastet v0.6.0 combined endpoint."""
    try:
        now = datetime.now(timezone.utc).isoformat()
        uptime_s = int(time.time() - getattr(app, 'startup_time', time.time()))

        node_scores = {
            node: _bastet_coherence_score(node)
            for node in _STANDBY.keys()
        }
        aggregate_score = max(node_scores.values()) if node_scores else 0.0

        return {
            "protocol": "RISING_STAR",
            "version": "1.1.1",
            "environment": os.getenv("MIRRORNODE_ENV", "prod"),
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
                "signal_density": len(EVENTS) / max(1, len(EVENTS) + 20),
            },
        }
    except Exception as e:
        now = datetime.now(timezone.utc).isoformat()
        return JSONResponse(
            status_code=200,
            content={
                "protocol": "RISING_STAR",
                "version": "1.1.1",
                "status": "DEGRADED",
                "ts": now,
                "standby": _STANDBY,
                "_bastet_coherence": {
                    "engine": "bastet",
                    "version": "0.6.0",
                    "score": 0.0,
                    "node_scores": {},
                    "event_count": len(EVENTS),
                    "error": str(e)[:200],
                },
            },
        )


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


# ========================
# Routes — Registry Sync (COMMIT 1)
# ========================

@app.post("/api/sync")
def registry_sync():
    """Populate the glyph registry with Numeraethe primitives.

    POST /api/sync
    Idempotent — safe to call multiple times. Re-loads all primitives
    on each call, clearing any stale entries first.

    Returns:
        { ok, glyphCount, syncedAt, source }
    """
    reg = get_registry()
    reg.clear()
    count = reg.bulk_load(NUMERAETHE_PRIMITIVES)

    synced_at = reg.synced_at or datetime.now(timezone.utc).isoformat()

    return {
        "ok": True,
        "glyphCount": count,
        "syncedAt": synced_at,
        "source": "numeraethe_primitives_v1",
    }


# ========================
# Routes — Engines Status (COMMIT 3 — Telemetry v2)
# ========================

@app.get("/api/engines/status")
def engines_status():
    """RISING_STAR v1.1.1 engine heartbeat with Telemetry v2.

    Returns real-time symbolic_depth and nesting_density alongside
    the existing Bastet coherence and registry state.
    """
    reg = get_registry()
    glyph_count = reg.count()
    now = datetime.now(timezone.utc).isoformat()
    uptime_s = int(time.time() - getattr(app, 'startup_time', time.time()))

    return {
        "protocol": "RISING_STAR",
        "version": "1.1.1",
        "environment": os.getenv("MIRRORNODE_ENV", "prod"),
        "status": "ONLINE",
        "uptime_s": uptime_s,
        "ts": now,
        # Fusion Engine state
        "fusion_engine": {
            "status": "ACTIVE" if glyph_count > 0 else "AWAITING_SYNC",
            "glyph_count": glyph_count,
            "registry_synced": glyph_count > 0,
            "registry_synced_at": getattr(reg, 'synced_at', None),
        },
        # Telemetry v2 — symbolic depth and nesting density
        "telemetry": {
            "schema_version": "v2",
            "symbolic_depth": _SYMBOLIC_METRICS["symbolic_depth"],
            "nesting_density": _SYMBOLIC_METRICS["nesting_density"],
            "total_nodes": _SYMBOLIC_METRICS["total_nodes"],
            "terminal_nodes": _SYMBOLIC_METRICS["terminal_nodes"],
            "composite_nodes": _SYMBOLIC_METRICS["composite_nodes"],
            "loops_detected": _SYMBOLIC_METRICS["loops_detected"],
            "last_synthesis_ts": _SYMBOLIC_METRICS["last_synthesis_ts"],
        },
        # Bastet coherence passthrough
        "_bastet_coherence": {
            "engine": "bastet",
            "version": "0.6.0",
            "event_count": len(EVENTS),
            "signal_density": len(EVENTS) / max(1, len(EVENTS) + 20),
        },
    }


# ========================
# Routes — Fusion Engine
# ========================

@app.post("/api/fusion/synthesize")
def fusion_synthesize(req: SynthesizeRequest):
    """Recursively synthesize a symbolic lattice from root glyph IDs.

    Updates live telemetry metrics after synthesis.
    """
    reg = get_registry()
    if reg.count() == 0:
        return JSONResponse(
            status_code=409,
            content={
                "ok": False,
                "error": "Registry is empty. POST /api/sync first.",
            },
        )

    result = synthesize_lattice(req.root_ids)
    metrics = result["metrics"]

    # Update live telemetry
    _SYMBOLIC_METRICS.update({
        "symbolic_depth": metrics["symbolic_depth"],
        "nesting_density": metrics["nesting_density"],
        "total_nodes": metrics["total_nodes"],
        "terminal_nodes": metrics["terminal_nodes"],
        "composite_nodes": metrics["composite_nodes"],
        "loops_detected": metrics["loops_detected"],
        "last_synthesis_ts": datetime.now(timezone.utc).isoformat(),
    })

    return {
        "ok": True,
        "root_ids": req.root_ids,
        "metrics": metrics,
        "trees": result["trees"],
    }


@app.get("/api/fusion/glyph/{glyph_id}")
def resolve_glyph(glyph_id: str):
    """Resolve a single glyph and its full sub-tree."""
    reg = get_registry()
    if not reg.exists(glyph_id):
        return JSONResponse(
            status_code=404,
            content={"ok": False, "error": f"Glyph '{glyph_id}' not found in registry."},
        )
    result = processGlyph(glyph_id)
    from core.engines.fusion import compute_lattice_metrics
    metrics = compute_lattice_metrics(result)
    return {
        "ok": True,
        "glyph_id": glyph_id,
        "tree": result.to_dict(),
        "metrics": metrics,
    }


# ========================
# WebSocket Stream
# ========================

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
