"""
MIRRORNODE :: Symbolic Engine v0.1
kernel/types.py

Re-exports only. Source of truth lives in mirrornode/symbolic/primitives.py.

This module exists for backward compatibility with any kernel-internal code
that imports from kernel.types. Do NOT define new symbolic dataclasses here.

Adding a new primitive:
  1. Define it in mirrornode/symbolic/primitives.py
  2. Add it to __all__ below
  3. Do not duplicate the definition here
"""

from mirrornode.symbolic.primitives import (  # noqa: F401
    # Result monad
    Ok,
    Err,
    Result,
    # Errors
    KernelError,
    KernelErrorCode,
    # Primitives
    Symbol,
    GlyphRef,
    SymbolicIntent,
    IntentKind,
    SymbolicState,
    SymbolStatus,
    SymbolicDelta,
    ResolutionResult,
)

__all__ = [
    # Result monad
    "Ok",
    "Err",
    "Result",
    # Errors
    "KernelError",
    "KernelErrorCode",
    # Primitives
    "Symbol",
    "GlyphRef",
    "SymbolicIntent",
    "IntentKind",
    "SymbolicState",
    "SymbolStatus",
    "SymbolicDelta",
    "ResolutionResult",
]
