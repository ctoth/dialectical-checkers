"""Phase 3a — tests for ``dialectical_checkers.evidence``.

``to_argument_evidence`` is the comorphism that turns a stringly-typed witness
label into typed :class:`ArgumentEvidence` carrying the witness's ``Value`` and
``Tier`` (design ``notes/checkers-design.md`` §4-5). Phase 3a covers the
FACT-tier labels of the §5 tables only — the HEURISTIC rows are Phase 5.

Every FACT label of design §5 is asserted here to map to the correct ``Value``
and ``Tier``, including the parsed magnitude where the label carries one.
"""

from __future__ import annotations

import pytest

from dialectical_checkers.evidence import ArgumentEvidence, to_argument_evidence
from dialectical_checkers.scheme import Tier, Value


# ---------------------------------------------------------------------------
# unit — every FACT-tier §5 label -> correct Value / Tier
# ---------------------------------------------------------------------------
#
# Each row: (label, expected Value, expected Tier). The magnitude-carrying
# labels are spot-checked separately for the parsed integer.

FACT_LABELS: list[tuple[str, Value, Tier]] = [
    # AS1 pro-reasons (design §5 first table, FACT rows).
    ("pro:terminal_win", Value.WINNING, Tier.FACT),
    ("pro:material:100", Value.MATERIAL, Tier.FACT),
    ("pro:material:250", Value.MATERIAL, Tier.FACT),
    ("pro:crown", Value.KING_COUNT, Tier.FACT),
    ("pro:shot_setup:200", Value.MATERIAL, Tier.FACT),
    # CQ-derived objections (design §5 second table, FACT rows).
    ("obj:terminal_loss", Value.WINNING, Tier.FACT),
    ("obj:allows_shot:100", Value.MATERIAL, Tier.FACT),
    ("obj:loses_exchange:150", Value.MATERIAL, Tier.FACT),
    # CQ17 reply attacks — FACT when the reply is a proven forced win/gain.
    ("reply:terminal_loss", Value.WINNING, Tier.FACT),
    ("reply:material:100", Value.MATERIAL, Tier.FACT),
    # A proven defense — answers a CQ8_9/CQ17 objection.
    ("defense:holds_exchange", Value.MATERIAL, Tier.FACT),
]


@pytest.mark.unit
@pytest.mark.parametrize(
    "label,value,tier",
    FACT_LABELS,
    ids=[row[0] for row in FACT_LABELS],
)
def test_fact_label_maps_to_value_and_tier(
    label: str, value: Value, tier: Tier
) -> None:
    """Every FACT-tier §5 label parses to the documented Value and FACT Tier."""
    evidence = to_argument_evidence(label)
    assert isinstance(evidence, ArgumentEvidence)
    assert evidence.label == label
    assert evidence.value is value
    assert evidence.tier is tier


@pytest.mark.unit
def test_every_fact_label_is_fact_tier() -> None:
    """No FACT-tier §5 label is ever mis-typed as HEURISTIC."""
    for label, _value, _tier in FACT_LABELS:
        assert to_argument_evidence(label).tier is Tier.FACT, label


# ---------------------------------------------------------------------------
# unit — magnitude parsing
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "label,magnitude",
    [
        ("pro:material:100", 100),
        ("pro:material:250", 250),
        ("pro:shot_setup:200", 200),
        ("obj:allows_shot:100", 100),
        ("obj:loses_exchange:150", 150),
        ("reply:material:100", 100),
    ],
    ids=lambda v: str(v),
)
def test_magnitude_is_parsed(label: str, magnitude: int) -> None:
    """A label carrying a ``:{n}`` magnitude parses ``n`` into ``magnitude``."""
    evidence = to_argument_evidence(label)
    assert evidence.magnitude == magnitude


@pytest.mark.unit
@pytest.mark.parametrize(
    "label",
    ["pro:terminal_win", "pro:crown", "obj:terminal_loss",
     "reply:terminal_loss", "defense:holds_exchange"],
)
def test_magnitudeless_labels_have_none_magnitude(label: str) -> None:
    """A label with no ``:{n}`` magnitude carries ``magnitude is None``."""
    assert to_argument_evidence(label).magnitude is None


# ---------------------------------------------------------------------------
# unit — malformed / unknown labels are rejected, never silently mistyped
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "label",
    [
        "",
        "pro:",
        "garbage",
        "pro:unknown_reason",
        "obj:unknown_objection",
        "pro:material",          # missing magnitude
        "pro:material:abc",      # non-numeric magnitude
        "obj:allows_shot",       # missing magnitude
        "pro:opposition",        # HEURISTIC §5 row — not implemented in 3a
    ],
)
def test_unknown_or_malformed_label_raises(label: str) -> None:
    """An unknown or malformed witness label raises rather than mistyping."""
    with pytest.raises(ValueError):
        to_argument_evidence(label)


@pytest.mark.unit
@pytest.mark.parametrize(
    "label",
    [
        # A ``{n}`` magnitude is a strictly positive material gain/loss
        # (design §5) — the witness producers only ever emit positive
        # magnitudes. A signed, ``+``-prefixed, or zero magnitude is malformed
        # and must be rejected, never accepted as valid FACT evidence.
        "pro:material:-100",     # negative magnitude
        "obj:allows_shot:-100",  # negative magnitude
        "reply:material:+100",   # explicit-plus-prefixed magnitude
        "pro:shot_setup:0",      # zero magnitude
        "pro:material:0",        # zero magnitude
        "obj:loses_exchange:0",  # zero magnitude
        "pro:material:00",       # zero magnitude with a leading zero
        "pro:material: 100",     # leading whitespace
    ],
)
def test_signed_or_zero_magnitude_raises(label: str) -> None:
    """A signed, ``+``-prefixed, or zero magnitude is rejected as malformed.

    Magnitudes for the FACT §5 labels are strictly positive integers; a
    negative, explicit-plus, or zero magnitude must raise rather than be
    silently accepted as typed FACT evidence.
    """
    with pytest.raises(ValueError):
        to_argument_evidence(label)
