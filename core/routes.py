from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from core.registry import register_agent, get_agents, emit_event, subscribe
import json

router = APIRouter()

@router.post("/agents/register")
async def agent_register(manifest: dict):
    return register_agent(manifest)

@router.get("/agents")
async def agents_list():
    return get_agents()

@router.post("/events/emit")
async def events_emit(event: dict):
    await emit_event(event)
    return {"status": "emitted"}

@router.get("/events/stream")
async def events_stream():
    q = subscribe()
    async def generator():
        while True:
            event = await q.get()
            yield f"data: {json.dumps(event)}\n\n"
    return StreamingResponse(generator(), media_type="text/event-stream")
