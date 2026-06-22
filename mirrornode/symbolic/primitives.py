"""
MIRRORNODE :: Symbolic Engine v0.1
mirrornode/symbolic/primitives.py

Source of truth for all symbolic dataclasses.
kernel/types.py re-exports from here — do not define these elsewhere.

Design rules:
  - All fields are immutable (frozen=True or FrozenField via tuples).
  - No unsafe_hash=True — deterministic __hash__ via frozen dataclasses.
  - Mutable collections (dict, list) replaced with tuple / FrozenSet.
  - resolve() must return Result[ResolutionResult, KernelError] — never bare ResolutionResult.
  - emit() is synchronous; async callers must await run_in_executor or use AsyncEmitter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Generic, Optional, Tuple, TypeVar, Union
import hashlib
import json


# ---------------------------------------------------------------------------
# Result[T, E] monad
# ---------------------------------------------------------------------------

T = TypeVar("T")
E = TypeVar("E")


@dataclass(frozen=True)
class Ok(Generic[T]):
    """Successful result wrapper."""

    value: T

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False

    def unwrap(self) -> T:
        return self.value

    def unwrap_err(self) -> None:
        raise ValueError("Called unwrap_err() on Ok")


@dataclass(frozen=True)
class Err(Generic[E]):
    """Error result wrapper."""

    error: E

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True

    def unwrap(self) -> None:
        raise ValueError(f"Called unwrap() on Err: {self.error}")

    def unwrap_err(self) -> E:
        return self.error


# Result[T, E] = Ok[T] | Err[E]
Result = Union[Ok[T], Err[E]]


# ---------------------------------------------------------------------------
# KernelError
# ---------------------------------------------------------------------------


class KernelErrorCode(Enum):
    UNKNOWN = auto()
    SYMBOL_NOT_FOUND = auto()
    GLYPH_INVALID = auto()
    INTENT_CONFLICT = auto()
    RESOLUTION_FAILED = auto()
    STATE_TRANSITION_INVALID = auto()
    DELTA_APPLY_FAILED = auto()
    EMIT_FAILED = auto()


@dataclass(frozen=True)
class KernelError:
    """Typed error for all symbolic engine operations."""

    code: KernelErrorCode
    message: str
    context: Tuple[Tuple[str, str], ...] = field(default_factory=tuple)

    @classmethod
    def of(
        cls,
        code: KernelErrorCode,
        message: str,
        **ctx: str,
    ) -> "KernelError":
        return cls(
            code=code,
            message=message,
            context=tuple(ctx.items()),
        )

    def __str__(self) -> str:
        ctx_str = ", ".join(f"{k}={v}" for k, v in self.context)
        return f"KernelError[{self.code.name}]: {self.message}" + (
            f" ({ctx_str})" if ctx_str else ""
        )


# ---------------------------------------------------------------------------
# Core symbolic primitives
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Symbol:
    """
    Atomic symbolic unit.

    id:      Stable identifier (e.g. 'LIGHT', 'SHADOW', 'THRESHOLD').
    label:   Human-readable label.
    domain:  Namespace / ontological domain (e.g. 'mythic', 'cognitive').
    tags:    Immutable tuple of classification tags.
    """

    id: str
    label: str
    domain: str
    tags: Tuple[str, ...] = field(default_factory=tuple)

    def digest(self) -> str:
        """Deterministic content hash — safe to use as dict key or DB PK."""
        payload = json.dumps(
            {"id": self.id, "label": self.label, "domain": self.domain},
            sort_keys=True,
        ).encode()
        return hashlib.sha256(payload).hexdigest()[:16]


@dataclass(frozen=True)
class GlyphRef:
    """
    Reference to a rendered glyph within a Symbol's visual layer.

    symbol_id:   Foreign key → Symbol.id
    glyph_key:   Unique key within the glyph registry.
    variant:     Optional rendering variant (e.g. 'dark', 'light', 'active').
    """

    symbol_id: str
    glyph_key: str
    variant: Optional[str] = None

    def qualified(self) -> str:
        return f"{self.symbol_id}::{self.glyph_key}" + (
            f"@{self.variant}" if self.variant else ""
        )


class IntentKind(Enum):
    INVOKE = auto()
    SUPPRESS = auto()
    TRANSFORM = auto()
    OBSERVE = auto()
    EMIT = auto()


@dataclass(frozen=True)
class SymbolicIntent:
    """
    Declared operator intent against a Symbol.

    symbol_id:   Target Symbol.id
    kind:        Intent classification.
    payload:     Immutable key-value pairs representing intent parameters.
    priority:    Dispatch priority (higher = sooner); default 0.
    """

    symbol_id: str
    kind: IntentKind
    payload: Tuple[Tuple[str, str], ...] = field(default_factory=tuple)
    priority: int = 0

    @classmethod
    def invoke(cls, symbol_id: str, **kwargs: str) -> "SymbolicIntent":
        return cls(
            symbol_id=symbol_id,
            kind=IntentKind.INVOKE,
            payload=tuple(kwargs.items()),
        )

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieve a payload value by key."""
        for k, v in self.payload:
            if k == key:
                return v
        return default


class SymbolStatus(Enum):
    DORMANT = auto()
    ACTIVE = auto()
    SUPPRESSED = auto()
    RESOLVING = auto()
    ERROR = auto()


@dataclass(frozen=True)
class SymbolicState:
    """
    Snapshot of a Symbol's runtime status.

    symbol_id:   Foreign key → Symbol.id
    status:      Current lifecycle status.
    epoch:       Monotonic epoch counter (increments on each state write).
    metadata:    Immutable key-value pairs for additional state context.
    """

    symbol_id: str
    status: SymbolStatus
    epoch: int = 0
    metadata: Tuple[Tuple[str, str], ...] = field(default_factory=tuple)

    def advance(self, new_status: SymbolStatus, **meta: str) -> "SymbolicState":
        """Return a new SymbolicState with incremented epoch."""
        merged = dict(self.metadata)
        merged.update(meta)
        return SymbolicState(
            symbol_id=self.symbol_id,
            status=new_status,
            epoch=self.epoch + 1,
            metadata=tuple(merged.items()),
        )


@dataclass(frozen=True)
class SymbolicDelta:
    """
    Atomic change descriptor: previous state → next state.

    Used for audit trails, replay, and conflict detection.

    symbol_id:   Foreign key → Symbol.id
    from_status: Status before the transition.
    to_status:   Status after the transition.
    intent_kind: The IntentKind that triggered the transition.
    actor:       Node or operator identity string.
    notes:       Free-form audit note (immutable).
    """

    symbol_id: str
    from_status: SymbolStatus
    to_status: SymbolStatus
    intent_kind: IntentKind
    actor: str
    notes: str = ""

    def to_audit_record(self) -> Tuple[Tuple[str, str], ...]:
        return (
            ("symbol_id", self.symbol_id),
            ("from", self.from_status.name),
            ("to", self.to_status.name),
            ("intent", self.intent_kind.name),
            ("actor", self.actor),
            ("notes", self.notes),
        )


@dataclass(frozen=True)
class ResolutionResult:
    """
    Output of a successful resolve() call.

    Always wrapped in Ok[ResolutionResult] — never returned bare.
    On failure, resolve() returns Err[KernelError].

    symbol_id:     Resolved Symbol.id
    final_state:   Resulting SymbolicState after resolution.
    delta:         The SymbolicDelta that was applied.
    glyphs:        Tuple of GlyphRefs activated during resolution.
    """

    symbol_id: str
    final_state: SymbolicState
    delta: SymbolicDelta
    glyphs: Tuple[GlyphRef, ...] = field(default_factory=tuple)

    def is_active(self) -> bool:
        return self.final_state.status == SymbolStatus.ACTIVE
