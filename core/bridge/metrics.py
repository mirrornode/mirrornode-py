"""
Prometheus metrics for MIRRORNODE Bridge
"""
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Event metrics
events_total = Counter(
    'mirrornode_events_total',
    'Total events processed',
    ['node', 'kind']
)

events_stored = Gauge(
    'mirrornode_events_stored',
    'Current number of events in memory'
)

# Connection metrics
websocket_clients = Gauge(
    'mirrornode_websocket_clients',
    'Active WebSocket connections'
)

# HTTP metrics
http_request_duration = Histogram(
    'mirrornode_http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)
