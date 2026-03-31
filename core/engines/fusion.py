"""Fusion Engine — Recursive Glyph Lattice Synthesizer.

Phase 3: Implements depth-first symbolic nesting with loop
detection and LRU caching for recurring patterns.
"""
from __future__ import annotations

import functools
from typing import Any, Dict, List, Optional, Set

from core.registry.cache import get_registry

# Maximum recursion depth before aborting traversal
MAX_DEPTH = 32


# ========================
# Glyph Processing Result
# ========================
class GlyphResult:
    """Carries the resolved symbolic node and traversal metadata."""

    def __init__(
        self,
        glyph_id: str,
        symbol: str,
        depth: int,
        children: Optional[List["GlyphResult"]] = None,
        terminal: bool = False,
        loop_detected: bool = False,
    ) -> None:
        self.glyph_id = glyph_id
        self.symbol = symbol
        self.depth = depth
        self.children: List[GlyphResult] = children or []
        self.terminal = terminal
        self.loop_detected = loop_detected

    def to_dict(self) -> Dict[str, Any]:
        return {
            "glyph_id": self.glyph_id,
            "symbol": self.symbol,
            "depth": self.depth,
            "terminal": self.terminal,
            "loop_detected": self.loop_detected,
            "children": [c.to_dict() for c in self.children],
        }


# ========================
# LRU Cache for Resolved Terminal Glyphs
# ========================
@functools.lru_cache(maxsize=512)
def _resolve_terminal(glyph_id: str) -> Optional[Dict[str, Any]]:
    """Cache terminal glyph lookups — these never change at runtime."""
    reg = get_registry()
    return reg.get(glyph_id)


# ========================
# Core Recursive Processor
# ========================
def processGlyph(
    glyph_id: str,
    depth: int = 0,
    visited: Optional[Set[str]] = None,
) -> GlyphResult:
    """Recursively resolve a glyph and all its sub-glyph references.

    Args:
        glyph_id: The ID of the glyph to resolve.
        depth: Current recursion depth (internal use).
        visited: Set of glyph IDs already on the current path (loop guard).

    Returns:
        GlyphResult tree rooted at glyph_id.
    """
    if visited is None:
        visited = set()

    # --- Loop detection ---
    if glyph_id in visited:
        return GlyphResult(
            glyph_id=glyph_id,
            symbol=f"[LOOP:{glyph_id}]",
            depth=depth,
            terminal=False,
            loop_detected=True,
        )

    # --- Depth guard ---
    if depth >= MAX_DEPTH:
        return GlyphResult(
            glyph_id=glyph_id,
            symbol=f"[MAX_DEPTH:{glyph_id}]",
            depth=depth,
            terminal=False,
            loop_detected=False,
        )

    reg = get_registry()
    glyph = reg.get(glyph_id)

    if glyph is None:
        return GlyphResult(
            glyph_id=glyph_id,
            symbol=f"[UNKNOWN:{glyph_id}]",
            depth=depth,
            terminal=True,
        )

    is_terminal: bool = glyph.get("terminal", True)
    refs: List[str] = glyph.get("refs", [])

    # Terminal glyphs — use LRU cache, no recursion needed
    if is_terminal or not refs:
        _resolve_terminal(glyph_id)  # warm the cache
        return GlyphResult(
            glyph_id=glyph_id,
            symbol=glyph.get("symbol", glyph_id),
            depth=depth,
            terminal=True,
        )

    # --- Recurse into sub-glyphs ---
    visited = visited | {glyph_id}  # immutable copy per branch
    children: List[GlyphResult] = [
        processGlyph(ref_id, depth=depth + 1, visited=visited)
        for ref_id in refs
    ]

    return GlyphResult(
        glyph_id=glyph_id,
        symbol=glyph.get("symbol", glyph_id),
        depth=depth,
        children=children,
        terminal=False,
    )


# ========================
# Lattice Metrics
# ========================
def compute_lattice_metrics(result: GlyphResult) -> Dict[str, Any]:
    """Walk a resolved GlyphResult tree and compute symbolic_depth
    and nesting_density for telemetry.

    Returns:
        {
          "symbolic_depth": int,    # max depth reached in traversal
          "nesting_density": float, # ratio of composite to terminal nodes
          "total_nodes": int,
          "terminal_nodes": int,
          "composite_nodes": int,
          "loops_detected": int,
        }
    """
    totals = {"total": 0, "terminal": 0, "composite": 0, "loops": 0, "max_depth": 0}

    def _walk(node: GlyphResult) -> None:
        totals["total"] += 1
        if node.depth > totals["max_depth"]:
            totals["max_depth"] = node.depth
        if node.loop_detected:
            totals["loops"] += 1
        elif node.terminal:
            totals["terminal"] += 1
        else:
            totals["composite"] += 1
        for child in node.children:
            _walk(child)

    _walk(result)

    density = (
        round(totals["composite"] / totals["total"], 4)
        if totals["total"] > 0
        else 0.0
    )

    return {
        "symbolic_depth": totals["max_depth"],
        "nesting_density": density,
        "total_nodes": totals["total"],
        "terminal_nodes": totals["terminal"],
        "composite_nodes": totals["composite"],
        "loops_detected": totals["loops"],
    }


def synthesize_lattice(root_ids: List[str]) -> Dict[str, Any]:
    """Entry point: synthesize a full lattice from a list of root glyph IDs.

    Returns resolved trees + aggregate metrics.
    """
    results = [processGlyph(gid) for gid in root_ids]
    trees = [r.to_dict() for r in results]

    # Aggregate metrics across all roots
    all_metrics = [compute_lattice_metrics(r) for r in results]
    max_depth = max((m["symbolic_depth"] for m in all_metrics), default=0)
    total_nodes = sum(m["total_nodes"] for m in all_metrics)
    total_terminal = sum(m["terminal_nodes"] for m in all_metrics)
    total_composite = sum(m["composite_nodes"] for m in all_metrics)
    total_loops = sum(m["loops_detected"] for m in all_metrics)

    return {
        "trees": trees,
        "metrics": {
            "symbolic_depth": max_depth,
            "nesting_density": round(total_composite / total_nodes, 4) if total_nodes else 0.0,
            "total_nodes": total_nodes,
            "terminal_nodes": total_terminal,
            "composite_nodes": total_composite,
            "loops_detected": total_loops,
        },
    }
