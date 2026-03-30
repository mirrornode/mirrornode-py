# MERLIN — MirrorNode Agent Spec

## Identity

| Field | Value |
|---|---|
| `node_id` | `merlin` |
| `role` | Orchestrator / Query Intelligence |
| `capabilities` | `orchestration`, `query_routing`, `context_synthesis` |
| `version` | `1.0.0` |

## Overview

Merlin is the orchestration and query-intelligence agent within the MirrorNode network.
It receives handoff events from peer nodes (Eve, Bastet, Thoth) via the Hermes protocol,
synthesizes context, and routes decisions or responses back through the event bus.

## Hermes Handshake

On connect to `/stream`, Merlin announces itself:

```json
{
  "node_id": "merlin",
  "capabilities": ["orchestration", "query_routing", "context_synthesis"]
}
```

## @mirror Handoff Protocol

Merlin is the designated escalation handler for `shadow_signal=True` events.
Peer nodes trigger a handoff via `POST /handoff/merlin`:

```json
{
  "from_node": "bastet",
  "reason": "coherence threshold exceeded",
  "payload": {
    "node": "oracle",
    "score": 0.87
  }
}
```

Merlin receives this as a `HANDOFF` kind `MirrorNodeEvent` broadcast on `/stream`
with `shadow_signal=True`, enabling all connected nodes to observe the escalation.

## Event Kinds Handled

| Kind | Description |
|---|---|
| `HANDOFF` | Directed handoff from a peer node |
| `ANALYSIS` | General analysis events for context synthesis |
| `STANDBY` | Node standby state changes |

## Notes

- Merlin does not mutate standby state directly — it observes and routes.
- All handoffs are traceable via `trace_id` in the event payload.
- Coherence scoring (Bastet) feeds Merlin's routing decisions.
