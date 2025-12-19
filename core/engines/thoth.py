from __future__ import annotations

class ThothEngine:
    """THOTH engine stub: invariants + verification hooks. No side effects."""

    def check_invariants(self, event: dict) -> list[str]:
        return []

    def sys_verification(self) -> list[str]:
        return []
