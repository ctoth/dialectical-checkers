"""Witness label -> typed ``ArgumentEvidence`` (design §5).

The comorphism that turns a stringly-typed witness label into typed evidence
carrying a ``Value``, a ``Tier`` and any parsed magnitude (design
``notes/checkers-design.md`` §4-5). dialectical-chess guessed evidence from
string prefixes; here every label is parsed once, in one place, into a closed
taxonomy — there is no prefix dispatch scattered through the codebase.

Phase 3a implements the **FACT-tier** rows of the design §5 tables only:

    pro:terminal_win            WINNING     FACT
    pro:material:{n}            MATERIAL    FACT
    pro:crown                   KING_COUNT  FACT
    pro:shot_setup:{n}          MATERIAL    FACT
    obj:terminal_loss           WINNING     FACT
    obj:allows_shot:{n}         MATERIAL    FACT
    obj:loses_exchange:{n}      MATERIAL    FACT
    reply:terminal_loss         WINNING     FACT
    reply:material:{n}          MATERIAL    FACT
    defense:holds_exchange      MATERIAL    FACT

The HEURISTIC §5 rows (``pro:opposition``, ``obj:back_rank_break``, …) are
Phase 5 — this module rejects them rather than silently mistyping them.

A ``:{n}`` magnitude is the resolver's native **weighted material** unit
(man = 100, king = 150) — the same unit ``captures.ShotResult.material_net``
and ``ResolvedLine.material_swing`` report. ``reply:`` and ``defense:`` are
emitted by ``witnesses.py`` only when the resolver *proved* the line, so they
are FACT here; their HEURISTIC forms (a truncated resolver line) are simply
never produced and therefore never reach this parser.

This module imports only from within ``dialectical_checkers`` and the stdlib.
"""

from __future__ import annotations

from dataclasses import dataclass

from dialectical_checkers.scheme import Tier, Value


@dataclass(frozen=True)
class ArgumentEvidence:
    """Typed evidence for one witness label (design §4-5).

    ``label`` is the original stringly-typed witness label; ``value`` is the
    AS2 value the witness promotes or demotes; ``tier`` is ``FACT`` for a
    resolver/terminal-proven witness and ``HEURISTIC`` for a positional one;
    ``magnitude`` is the parsed ``:{n}`` integer (weighted material) when the
    label carries one, else ``None``.
    """

    label: str
    value: Value
    tier: Tier
    magnitude: int | None = None


# --- the FACT-tier label taxonomy (design §5) -------------------------------
#
# Two tables. ``_FIXED`` — labels with no magnitude, mapped directly to their
# (Value, Tier). ``_MAGNITUDE`` — label prefixes that MUST carry a ``:{n}``
# integer magnitude, mapped to their (Value, Tier). Splitting them keeps the
# parser a pair of dict lookups with no per-label branching.

_FIXED: dict[str, tuple[Value, Tier]] = {
    "pro:terminal_win": (Value.WINNING, Tier.FACT),
    "pro:crown": (Value.KING_COUNT, Tier.FACT),
    "obj:terminal_loss": (Value.WINNING, Tier.FACT),
    "reply:terminal_loss": (Value.WINNING, Tier.FACT),
    "defense:holds_exchange": (Value.MATERIAL, Tier.FACT),
}

_MAGNITUDE: dict[str, tuple[Value, Tier]] = {
    "pro:material": (Value.MATERIAL, Tier.FACT),
    "pro:shot_setup": (Value.MATERIAL, Tier.FACT),
    "obj:allows_shot": (Value.MATERIAL, Tier.FACT),
    "obj:loses_exchange": (Value.MATERIAL, Tier.FACT),
    "reply:material": (Value.MATERIAL, Tier.FACT),
}


def to_argument_evidence(label: str) -> ArgumentEvidence:
    """Map a witness label to typed :class:`ArgumentEvidence` (design §5).

    A fixed label (no magnitude) is looked up directly. A magnitude-carrying
    label has the form ``<prefix>:<n>`` where ``<n>`` is a base-10 integer;
    the prefix is looked up and ``<n>`` parsed into ``magnitude``.

    Raises :class:`ValueError` for an empty, malformed, or unknown label, or
    for a magnitude label whose ``:{n}`` part is missing or non-numeric —
    Phase 3a never silently mistypes a label, and the HEURISTIC §5 rows
    (Phase 5) are unknown to this parser and so are rejected.
    """
    if not label:
        raise ValueError("empty witness label")

    fixed = _FIXED.get(label)
    if fixed is not None:
        value, tier = fixed
        return ArgumentEvidence(label=label, value=value, tier=tier)

    # A magnitude label is ``<prefix>:<n>`` — split off the trailing ``:<n>``.
    head, sep, tail = label.rpartition(":")
    if not sep:
        raise ValueError(f"unknown witness label {label!r}")
    mag = _MAGNITUDE.get(head)
    if mag is None:
        raise ValueError(f"unknown witness label {label!r}")
    try:
        magnitude = int(tail)
    except ValueError:
        raise ValueError(
            f"witness label {label!r} has a non-integer magnitude {tail!r}"
        ) from None
    value, tier = mag
    return ArgumentEvidence(
        label=label, value=value, tier=tier, magnitude=magnitude
    )
