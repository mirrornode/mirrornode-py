# MirrorNode Python Bridge Integration (v1)

**Status:** Frozen / Proven  
**Last verified:** 2026-01-22

This document describes the Python FastAPI bridge service that accepts events
from TypeScript clients and exposes Prometheus metrics.

For the complete integration documentation including TypeScript client usage,
see: [TypeScript repo docs/bridge-integration.md](https://github.com/mirrornode/mirrornode/blob/main/docs/bridge-integration.md)

---

## Service

**Local URL:** `http://localhost:8420`

### Endpoints

- `GET /health` - Service liveness check
- `POST /events` - Ingest event
- `GET /events/recent?limit=N` - Retrieve recent events
- `WebSocket /stream` - Real-time event stream
- `GET /metrics` - Prometheus metrics

### Event Schema

**Required fields:**
- `kind` (string) - Event type
- `node` (string) - Source identifier
- `payload` (object, optional) - Event data

**Bridge adds automatically:**
- `id` (UUID) if not provided
- `ts` (ISO timestamp) if not provided

---

## Prometheus Metrics

### Exposed Metrics

- `mirrornode_events_total{kind,node}` - Total events by type/source
- `mirrornode_events_stored` - In-memory event count
- `mirrornode_websocket_clients` - Active WS connections
- `mirrornode_http_request_duration_seconds{method,endpoint}` - Request latency

### Performance

- Event ingestion: ~3–5ms
- Metrics scrape: <10ms

---

## Running Locally

```bash
cd ~/dev/mirrornode-py
source .venv/bin/activate
uvicorn core.bridge.main:app --host 0.0.0.0 --port 8420 --reload

# Health check
curl http://localhost:8420/health

# Post event
curl -X POST http://localhost:8420/events \
  -H "Content-Type: application/json" \
  -d '{"kind":"TEST","node":"curl","payload":{}}'

# Check metrics
curl http://localhost:8420/metrics | grep mirrornode

Implementation Files
core/bridge/main.py - FastAPI app and endpoints

core/bridge/metrics.py - Prometheus metric definitions


fastapi==0.104.1
uvicorn[standard]
prometheus-client==0.24.1
pydantic>=2.0

Frozen Scope (v1)
Includes:

In-memory event storage

WebSocket broadcast

Prometheus metrics

Basic health check

Explicitly excludes:

Persistence (DB, disk)

Authentication

Rate limiting

Schema validation beyond minimal fields

Change Policy
Changes to endpoints, schemas, or metrics require:

Documentation update in both repos

Version bump

Integration test validation
