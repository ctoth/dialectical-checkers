"""Witness label -> typed ``ArgumentEvidence``.

Phase 0 skeleton. The comorphism that turns a stringly-typed witness label
into typed evidence carrying a ``Value`` and a ``Tier`` (design §4-5) is built
alongside the witnesses in Phases 3 and 5. Nothing here is implemented yet.
"""

from __future__ import annotations

from dataclasses import dataclass

from dialectical_checkers.scheme import Tier, Value


@dataclass(frozen=True)
class ArgumentEvidence:
    """Typed evidence for one witness label (design §4-5)."""

    label: str
    value: Value
    tier: Tier


def to_argument_evidence(label: str) -> ArgumentEvidence:
    """Map a witness label to typed evidence (design §5). Built in Phase 3."""
    raise NotImplementedError
