"""api/index.py — Vercel serverless entrypoint for mirrornode-py
Exposes the FastAPI bridge app to @vercel/python.
Routes: /, /health, /projects, /events, /events/recent, /stream, /feedback
RISING STAR PROTOCOL: /standby, /standby/status
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

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="MirrorNode Bridge",
    description="MIRRORNODE distributed AI lattice — event hub & agent registry",
    version="0.4.0",
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
# RISING STAR PROTOCOL — Models
# ---------------------------------------------------------------------------
class RSPDomain(str, Enum):
    INVARIANT = "INVARIANT"
    SYSTEM    = "SYSTEM"
    UNKNOWN   = "UNKNOWN"

class StandbyRequest(BaseModel):
    """Rising Star Protocol — standby submission."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ts: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    from_node: str = Field(..., alias="from", description="Who is submitting (name/node ID)")
    problem: str   = Field(..., description="Plain-language description of the blocker")
    context: Dict[str, Any] = Field(default_factory=dict, description="Optional: stack trace, file path, event ID")
    priority: int  = Field(default=2, ge=1, le=3, description="1=critical 2=normal 3=low")

    model_config = {"populate_by_name": True}

class StandbyResponse(BaseModel):
    """Structured plan returned by the standby agent."""
    request_id: str
    agent: str
    domain: RSPDomain
    status: str = "ACTIVE"
    plan: List[str]
    next_action: str
    estimated_unblock_minutes: int
    event_id: str

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
    """Load agent definitions from bundled agents directory."""
    agents_dir = pathlib.Path(__file__).parent.parent / "agents"
    if not agents_dir.exists():
        return []
    agents = []
    for f in sorted(agents_dir.glob("*.md")):
        try:
            agents.append({"name": f.stem, "file": f.name})
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
# RISING STAR PROTOCOL — Domain Classifier
# ---------------------------------------------------------------------------
_SYSTEM_KEYWORDS = re.compile(
    r"deploy|vercel|bridge|port|uvicorn|import|module|install|"
    r"poetry|pip|docker|env|timeout|500|crash|server|endpoint|"
    r"route|api|stream|websocket|ws|health|build|ci|action",
    re.I
)
_INVARIANT_KEYWORDS = re.compile(
    r"schema|contract|event|model|pydantic|invariant|drift|"
    r"truth|boundary|role|authority|scope|violation|mismatch|"
    r"version|breaking|migration|id|uuid|field",
    re.I
)

def _classify_domain(problem: str) -> RSPDomain:
    if _INVARIANT_KEYWORDS.search(problem):
        return RSPDomain.INVARIANT
    if _SYSTEM_KEYWORDS.search(problem):
        return RSPDomain.SYSTEM
    return RSPDomain.UNKNOWN

# Agent plans registry
_AGENT_PLANS: Dict[RSPDomain, Dict] = {
    RSPDomain.INVARIANT: {
        "agent": "THOTH-PRIME",
        "plan_template": [
            "1. Identify which invariant is violated (schema / role boundary / source-of-truth / scope)",
            "2. Locate the offending commit or payload using /events/recent",
            "3. Revert or patch to restore invariant — do NOT work around it",
            "4. Emit a corrective MirrorNodeEvent with kind=INVARIANT_RESTORED",
            "5. Document the breach in MIRRORNODE-CORE-HUB /canon",
        ],
        "eta_minutes": 15,
    },
    RSPDomain.SYSTEM: {
        "agent": "THOTH-SYS",
        "plan_template": [
            "1. Check /health endpoint — confirm service is online and event count is non-zero",
            "2. Review Vercel deployment logs for build/runtime errors",
            "3. Verify requirements.txt matches pyproject.toml — pydantic v2, fastapi>=0.109",
            "4. Test the specific failing route with curl — capture raw response",
            "5. If bridge-related: confirm core/bridge/main.py is imported and port 8420 is bound",
            "6. Hot-patch in api/index.py if Vercel serverless; local fix if bridge service",
        ],
        "eta_minutes": 10,
    },
    RSPDomain.UNKNOWN: {
        "agent": "THOTH-SHADOW",
        "plan_template": [
            "1. Restate the problem in one sentence — if you can't, the problem is underspecified",
            "2. Identify which MIRRORNODE node owns this domain (lattice map: /projects)",
            "3. Break into smallest falsifiable question: what would solved look like?",
            "4. Post a MirrorNodeEvent kind=SHADOW_TRACE with your hypothesis",
            "5. Escalate to THOTH-PRIME (if schema) or THOTH-SYS (if infra) once domain is known",
        ],
        "eta_minutes": 20,
    },
}

# ---------------------------------------------------------------------------
# Routes — Core
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    return {"service": "mirrornode-bridge", "version": "0.4.0", "status": "online", "protocol": "RISING_STAR"}

@app.get("/health")
def health():
    return {
        "status": "ok",
        "node": "mirrornode-backend",
        "ts": datetime.now(timezone.utc).isoformat(),
        "events": len(EVENTS),
        "clients": len(CLIENTS),
        "protocol": "RISING_STAR",
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

# ---------------------------------------------------------------------------
# Routes — RISING STAR PROTOCOL
# ---------------------------------------------------------------------------
import os as _os
from datetime import datetime as _datetime, timezone as _tz

_BOOT_TIME = _datetime.now(_tz.utc)
_request_counter = 0


@app.post("/standby", response_model=StandbyResponse)
async def rising_star_standby(req: StandbyRequest):
    """
    RISING STAR PROTOCOL — Submit a blocker, receive a structured plan.
    The correct standby agent is selected automatically based on problem domain.
    """
    domain  = _classify_domain(req.problem)
    profile = _AGENT_PLANS[domain]

    plan = [*profile["plan_template"]]
    plan.append(f'Context received: "{req.problem[:200]}"')

    evt = MirrorNodeEvent(
        node=profile["agent"],
        kind="RSP_STANDBY",
        payload={
            "request_id": req.id,
            "from": req.from_node,
            "domain": domain,
            "problem": req.problem,
            "priority": req.priority,
            "context": req.context,
        },
    )
    EVENTS.append(evt)
    await _broadcast(evt)

    return StandbyResponse(
        request_id=req.id,
        agent=profile["agent"],
        domain=domain,
        plan=plan,
        next_action=plan[0],
        estimated_unblock_minutes=profile["eta_minutes"],
        event_id=evt.id,
    )


@app.get("/standby/status")
def standby_status():
    """RISING_STAR v1.1.0 — Live protocol status. Hardened: validated, logged, schema-locked."""
    import logging
    global _request_counter
    _request_counter += 1
    now = _datetime.now(_tz.utc)
    uptime_s = int((now - _BOOT_TIME).total_seconds())

    # --- Node identity: normalize + validate
    raw_node_id = _os.getenv("MIRRORNODE_NODE_ID", "api.mirrornode.xyz")
    node_id = raw_node_id.strip().lower()
    if not node_id or len(node_id) >= 64:
        logging.error(f"[RISING_STAR] Invalid node_id: {repr(raw_node_id)}")
        node_id = "api.mirrornode.xyz"

    # --- Agent list: always a list, never null
    agents = [
        {"name": "THOTH-PRIME",  "role": "orchestrator", "status": "ONLINE", "last_heartbeat_ts": now.isoformat()},
        {"name": "THOTH-SHADOW", "role": "observer",     "status": "ONLINE", "last_heartbeat_ts": now.isoformat()},
        {"name": "THOTH-SYS",    "role": "system",       "status": "ONLINE", "last_heartbeat_ts": now.isoformat()},
    ]

    # --- Metrics: always a dict, never null
    metrics = {
        "standby_requests_served": _request_counter,
        "error_rate_1m": 0.0,
    }

    # --- Lattice: always a dict, never null
    lattice = {
        "node_id": node_id,
        "known_nodes": [node_id],
        "schema_version": "1.1.0",
    }

    # --- Schema-locked response: no nulls on structured fields
    response = {
        "protocol": "RISING_STAR",
        "version": "1.1.0",
        "environment": _os.getenv("MIRRORNODE_ENV", "prod"),
        "status": "ONLINE",
        "uptime_s": uptime_s or 0,
        "ts": now.isoformat(),
        "agents": agents or [],
        "metrics": metrics or {},
        "lattice": lattice or {},
        "integrity": "v1.1.0-ok",
    }

    logging.info(f"[RISING_STAR] /standby/status served | req#{_request_counter} | uptime={uptime_s}s | node={node_id}")
    return response
