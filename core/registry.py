from typing import Dict, Any
import asyncio

_agents: Dict[str, Any] = {}
_subscribers: list = []

def register_agent(manifest: dict) -> dict:
    node_id = manifest["node_id"]
    _agents[node_id] = manifest
    return {"status": "registered", "node_id": node_id}

def get_agents() -> list:
    return list(_agents.values())

async def emit_event(event: dict):
    dead = []
    for q in _subscribers:
        try:
            await q.put(event)
        except Exception:
            dead.append(q)
    for q in dead:
        _subscribers.remove(q)

def subscribe() -> asyncio.Queue:
    q = asyncio.Queue()
    _subscribers.append(q)
    return q
