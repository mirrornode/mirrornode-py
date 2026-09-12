"""GlyphCache adapter — abstract interface for registry persistence.

Phase 3: InMemoryCache is the default implementation.
Phase 4: Swap to UpstashCache without touching call sites.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


# ========================
# Numeraethe Primitive Seed Data
# ========================
# Core symbolic primitives loaded at sync time.
# Extend this list from canon/glyph-index as the lattice grows.
NUMAEREATHE_PRIMITIVES: List[Dict[str, Any]] = [
    {"id": "NM-001", "symbol": "Aeth",     "class": "root",      "terminal": True,  "refs": []},
    {"id": "NM-002", "symbol": "Vyr",      "class": "root",      "terminal": True,  "refs": []},
    {"id": "NM-003", "symbol": "Sorath",   "class": "composite", "terminal": False, "refs": ["NM-001", "NM-002"]},
    {"id": "NM-004", "symbol": "Lethis",   "class": "root",      "terminal": True,  "refs": []},
    {"id": "NM-005", "symbol": "Caelum",   "class": "composite", "terminal": False, "refs": ["NM-002", "NM-004"]},
    {"id": "NM-006", "symbol": "Praex",    "class": "root",      "terminal": True,  "refs": []},
    {"id": "NM-007", "symbol": "Threnody", "class": "composite", "terminal": False, "refs": ["NM-003", "NM-006"]},
    {"id": "NM-008", "symbol": "Vorath",   "class": "lattice",   "terminal": False, "refs": ["NM-005", "NM-007"]},
    {"id": "NM-009", "symbol": "Ixael",    "class": "root",      "terminal": True,  "refs": []},
    {"id": "NM-010", "symbol": "Meraxis",  "class": "lattice",   "terminal": False, "refs": ["NM-008", "NM-009"]},
]


# ========================
# Abstract Cache Interface
# ========================
class GlyphCache(ABC):
    """Abstract base — all implementations must satisfy this contract."""

    @abstractmethod
    def get(self, glyph_id: str) -> Optional[Dict[str, Any]]:
        """Return glyph by ID or None."""
        ...

    @abstractmethod
    def set(self, glyph_id: str, data: Dict[str, Any]) -> None:
        """Store or update a glyph."""
        ...

    @abstractmethod
    def exists(self, glyph_id: str) -> bool:
        """Return True if glyph_id is present."""
        ...

    @abstractmethod
    def keys(self) -> List[str]:
        """Return all registered glyph IDs."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Return number of registered glyphs."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Flush all entries."""
        ...


# ========================
# In-Memory Implementation (Phase 3 Default)
# ========================
class InMemoryCache(GlyphCache):
    """Singleton in-memory registry. Fast, no cold-start latency.
    Not persistent across Vercel cold starts — see UpstashCache for Phase 4.
    """

    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}
        self._synced_at: Optional[str] = None

    def get(self, glyph_id: str) -> Optional[Dict[str, Any]]:
        return self._store.get(glyph_id)

    def set(self, glyph_id: str, data: Dict[str, Any]) -> None:
        self._store[glyph_id] = data

    def exists(self, glyph_id: str) -> bool:
        return glyph_id in self._store

    def keys(self) -> List[str]:
        return list(self._store.keys())

    def count(self) -> int:
        return len(self._store)

    def clear(self) -> None:
        self._store.clear()
        self._synced_at = None

    def bulk_load(self, glyphs: List[Dict[str, Any]]) -> int:
        """Load a list of glyph dicts. Returns count loaded."""
        for g in glyphs:
            self._store[g["id"]] = g
        self._synced_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        return len(glyphs)

    @property
    def synced_at(self) -> Optional[str]:
        return self._synced_at


# ========================
# Upstash Redis Stub (Phase 4)
# ========================
class UpstashCache(GlyphCache):  # pragma: no cover
    """Redis-backed persistent cache via Upstash REST API.

    Phase 4 implementation guide:
    1. pip install upstash-redis
    2. Set UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN in Vercel env vars
    3. Replace InMemoryCache with UpstashCache in _GLYPH_REGISTRY init below
    4. bulk_load() writes all primitives to Redis with pipeline for efficiency
    5. get/set/exists delegate to upstash_redis.Redis client

    Performance note (1,500–5,000 glyphs):
    - Upstash free tier: ~10ms avg latency per GET from us-east-1
    - Use HGETALL on a single hash key for bulk reads vs. N individual GETs
    - Cold start re-hydration: ~50–120ms for 5k glyphs via pipeline
    - Recommend TTL=0 (no expiry) for core primitives; TTL=3600 for derived lattice nodes
    """

    def __init__(self) -> None:
        raise NotImplementedError(
            "UpstashCache is not yet wired. "
            "Set UPSTASH_REDIS_REST_URL + UPSTASH_REDIS_REST_TOKEN env vars first."
        )

    def get(self, glyph_id: str) -> Optional[Dict[str, Any]]: ...
    def set(self, glyph_id: str, data: Dict[str, Any]) -> None: ...
    def exists(self, glyph_id: str) -> bool: ...
    def keys(self) -> List[str]: ...
    def count(self) -> int: ...
    def clear(self) -> None: ...


# ========================
# Singleton Registry Instance
# ========================
_GLYPH_REGISTRY: GlyphCache = InMemoryCache()


def get_registry() -> GlyphCache:
    """Return the active registry singleton."""
    return _GLYPH_REGISTRY
