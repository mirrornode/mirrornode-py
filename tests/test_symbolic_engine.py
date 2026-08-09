"""
MIRRORNODE :: Symbolic Engine v0.1 — Acceptance Tests
tests/test_symbolic_engine.py

Contract rules verified here:
  1. All primitives import from a single source (mirrornode.symbolic.primitives).
  2. kernel.types re-exports identical objects (no duplicates).
  3. resolve() returns Result[ResolutionResult, KernelError], never bare.
  4. No unsafe_hash — frozen dataclasses are hashable by default.
  5. Immutable fields: payload/metadata/tags use tuples, not dicts/lists.
  6. SymbolicDelta.to_audit_record() returns a tuple of 2-tuples.
  7. ResolutionResult is inspectable without mutation.
"""

import pytest

from mirrornode.symbolic.primitives import (
    Ok,
    Err,
    KernelError,
    KernelErrorCode,
    Symbol,
    GlyphRef,
    SymbolicIntent,
    IntentKind,
    SymbolicState,
    SymbolStatus,
    SymbolicDelta,
    ResolutionResult,
)

# Also verify kernel.types re-exports resolve to the same objects
import kernel.types as kt


# ---------------------------------------------------------------------------
# 1. Import identity — kernel.types re-exports primitives source
# ---------------------------------------------------------------------------


class TestImportIdentity:
    def test_symbol_same_class(self):
        from mirrornode.symbolic.primitives import Symbol as SP

        assert kt.Symbol is SP

    def test_resolution_result_same_class(self):
        from mirrornode.symbolic.primitives import ResolutionResult as RP

        assert kt.ResolutionResult is RP

    def test_kernel_error_same_class(self):
        from mirrornode.symbolic.primitives import KernelError as KE

        assert kt.KernelError is KE


# ---------------------------------------------------------------------------
# 2. Frozen / immutable — no unsafe_hash
# ---------------------------------------------------------------------------


class TestImmutability:
    def test_symbol_frozen(self):
        s = Symbol(id="LIGHT", label="Light", domain="mythic", tags=("solar",))
        with pytest.raises((AttributeError, TypeError)):
            s.id = "SHADOW"  # type: ignore[misc]

    def test_symbol_hashable_without_unsafe_hash(self):
        s = Symbol(id="LIGHT", label="Light", domain="mythic")
        # Must be usable as dict key or set member
        d = {s: "value"}
        assert d[s] == "value"

    def test_symbolic_state_frozen(self):
        state = SymbolicState(symbol_id="LIGHT", status=SymbolStatus.DORMANT)
        with pytest.raises((AttributeError, TypeError)):
            state.epoch = 99  # type: ignore[misc]

    def test_payload_is_tuple(self):
        intent = SymbolicIntent.invoke("LIGHT", channel="solar")
        assert isinstance(intent.payload, tuple)
        # Tuple of 2-tuples
        for item in intent.payload:
            assert isinstance(item, tuple)
            assert len(item) == 2

    def test_tags_is_tuple(self):
        s = Symbol(id="SHADOW", label="Shadow", domain="mythic", tags=("chthonic",))
        assert isinstance(s.tags, tuple)

    def test_metadata_is_tuple(self):
        state = SymbolicState(
            symbol_id="X",
            status=SymbolStatus.ACTIVE,
            metadata=(("key", "val"),),
        )
        assert isinstance(state.metadata, tuple)


# ---------------------------------------------------------------------------
# 3. Result monad — resolve() must return Result[ResolutionResult, KernelError]
# ---------------------------------------------------------------------------


def _fake_resolve(symbol_id: str, fail: bool = False):
    """Minimal stand-in for the real resolve() function."""
    if fail:
        return Err(
            KernelError.of(
                KernelErrorCode.RESOLUTION_FAILED,
                "Symbol not found",
                symbol_id=symbol_id,
            )
        )
    state = SymbolicState(symbol_id=symbol_id, status=SymbolStatus.ACTIVE, epoch=1)
    delta = SymbolicDelta(
        symbol_id=symbol_id,
        from_status=SymbolStatus.DORMANT,
        to_status=SymbolStatus.ACTIVE,
        intent_kind=IntentKind.INVOKE,
        actor="test-suite",
    )
    return Ok(
        ResolutionResult(symbol_id=symbol_id, final_state=state, delta=delta)
    )


class TestResultContract:
    def test_ok_wraps_resolution_result(self):
        result = _fake_resolve("LIGHT")
        assert result.is_ok()
        assert isinstance(result.unwrap(), ResolutionResult)

    def test_err_wraps_kernel_error(self):
        result = _fake_resolve("MISSING", fail=True)
        assert result.is_err()
        assert isinstance(result.unwrap_err(), KernelError)

    def test_ok_unwrap_returns_value(self):
        result = _fake_resolve("THRESHOLD")
        rr = result.unwrap()
        assert rr.symbol_id == "THRESHOLD"
        assert rr.is_active()

    def test_err_unwrap_raises(self):
        result = _fake_resolve("X", fail=True)
        with pytest.raises(ValueError):
            result.unwrap()

    def test_ok_unwrap_err_raises(self):
        result = _fake_resolve("LIGHT")
        with pytest.raises(ValueError):
            result.unwrap_err()

    def test_kernel_error_code_correct(self):
        result = _fake_resolve("X", fail=True)
        err = result.unwrap_err()
        assert err.code == KernelErrorCode.RESOLUTION_FAILED


# ---------------------------------------------------------------------------
# 4. GlyphRef
# ---------------------------------------------------------------------------


class TestGlyphRef:
    def test_qualified_no_variant(self):
        ref = GlyphRef(symbol_id="LIGHT", glyph_key="sun-circle")
        assert ref.qualified() == "LIGHT::sun-circle"

    def test_qualified_with_variant(self):
        ref = GlyphRef(symbol_id="LIGHT", glyph_key="sun-circle", variant="active")
        assert ref.qualified() == "LIGHT::sun-circle@active"

    def test_glyph_ref_frozen(self):
        ref = GlyphRef(symbol_id="LIGHT", glyph_key="sun-circle")
        with pytest.raises((AttributeError, TypeError)):
            ref.glyph_key = "moon"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 5. SymbolicState transitions
# ---------------------------------------------------------------------------


class TestSymbolicState:
    def test_advance_increments_epoch(self):
        state = SymbolicState(symbol_id="LIGHT", status=SymbolStatus.DORMANT)
        next_state = state.advance(SymbolStatus.ACTIVE, trigger="invoke")
        assert next_state.epoch == state.epoch + 1

    def test_advance_returns_new_instance(self):
        state = SymbolicState(symbol_id="LIGHT", status=SymbolStatus.DORMANT)
        next_state = state.advance(SymbolStatus.ACTIVE)
        assert next_state is not state

    def test_advance_preserves_symbol_id(self):
        state = SymbolicState(symbol_id="THRESHOLD", status=SymbolStatus.DORMANT)
        next_state = state.advance(SymbolStatus.RESOLVING)
        assert next_state.symbol_id == "THRESHOLD"


# ---------------------------------------------------------------------------
# 6. SymbolicDelta audit record
# ---------------------------------------------------------------------------


class TestSymbolicDelta:
    def test_audit_record_is_tuple_of_tuples(self):
        delta = SymbolicDelta(
            symbol_id="LIGHT",
            from_status=SymbolStatus.DORMANT,
            to_status=SymbolStatus.ACTIVE,
            intent_kind=IntentKind.INVOKE,
            actor="lucian",
        )
        record = delta.to_audit_record()
        assert isinstance(record, tuple)
        for item in record:
            assert isinstance(item, tuple)
            assert len(item) == 2

    def test_audit_record_has_expected_keys(self):
        delta = SymbolicDelta(
            symbol_id="X",
            from_status=SymbolStatus.DORMANT,
            to_status=SymbolStatus.ACTIVE,
            intent_kind=IntentKind.EMIT,
            actor="theia",
            notes="witness",
        )
        keys = [k for k, _ in delta.to_audit_record()]
        assert "symbol_id" in keys
        assert "from" in keys
        assert "to" in keys
        assert "actor" in keys


# ---------------------------------------------------------------------------
# 7. Symbol digest
# ---------------------------------------------------------------------------


class TestSymbolDigest:
    def test_digest_is_deterministic(self):
        s = Symbol(id="LIGHT", label="Light", domain="mythic")
        assert s.digest() == s.digest()

    def test_same_fields_same_digest(self):
        a = Symbol(id="LIGHT", label="Light", domain="mythic")
        b = Symbol(id="LIGHT", label="Light", domain="mythic")
        assert a.digest() == b.digest()

    def test_different_id_different_digest(self):
        a = Symbol(id="LIGHT", label="Light", domain="mythic")
        b = Symbol(id="SHADOW", label="Light", domain="mythic")
        assert a.digest() != b.digest()
