"""Witness label -> typed ``ArgumentEvidence`` (design §5).

The comorphism that turns a stringly-typed witness label into typed evidence
carrying a ``Value``, a ``Tier`` and any parsed magnitude (design
``notes/checkers-design.md`` §4-5). dialectical-chess guessed evidence from
string prefixes; here every label is parsed once, in one place, into a closed
taxonomy — there is no prefix dispatch scattered through the codebase.

Phase 3a implements the **FACT-tier** rows of the design §5 tables only:

    pro:terminal_win                  WINNING     FACT
    pro:material:{n}                  MATERIAL    FACT
    pro:crown                         KING_COUNT  FACT
    pro:shot_setup:{n}                MATERIAL    FACT
    obj:terminal_loss                 WINNING     FACT
    obj:allows_shot:{n}               MATERIAL    FACT
    obj:loses_exchange:{n}            MATERIAL    FACT
    reply:terminal_loss               WINNING     FACT
    reply:material:{n}                MATERIAL    FACT
    defense:holds_exchange@{answered} MATERIAL    FACT

A ``defense:`` label is **keyed to the specific objection / reply it answers**
(design §6 — "a defense defeats the objection/reply it answers, and only that
one"). The keyed form is ``defense:holds_exchange@{answered}`` where
``{answered}`` is itself a valid FACT objection / reply label (e.g.
``defense:holds_exchange@reply:material:100``). The ``answered`` field on the
parsed :class:`ArgumentEvidence` carries the target label so the crisp layer
(``arguments.py``) can wire the defense to *only* that attacker. The bare,
un-keyed ``defense:holds_exchange`` is still accepted by this parser (it is a
valid evidence type) but ``witnesses.py`` never emits it — every emitted
defense carries its target.

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
    label carries one, else ``None``; ``answered`` is the objection / reply
    label a keyed ``defense:`` witness answers (design §6 "and only that one"),
    else ``None``.
    """

    label: str
    value: Value
    tier: Tier
    magnitude: int | None = None
    answered: str | None = None


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


# --- keyed defense labels (design §6) ---------------------------------------
#
# A defense is keyed to the objection / reply it answers with an ``@``
# separator: ``defense:holds_exchange@reply:material:100``. The part before the
# ``@`` is a bare defense type (it must be in ``_FIXED`` and be a ``defense:``
# label); the part after is the answered objection / reply label, itself parsed
# recursively so a malformed target is rejected.

_DEFENSE_KEY_SEP = "@"


def to_argument_evidence(label: str) -> ArgumentEvidence:
    """Map a witness label to typed :class:`ArgumentEvidence` (design §5).

    A fixed label (no magnitude) is looked up directly. A magnitude-carrying
    label has the form ``<prefix>:<n>`` where ``<n>`` is a base-10 integer;
    the prefix is looked up and ``<n>`` parsed into ``magnitude``. A keyed
    defense label has the form ``<defense-type>@<answered>`` where
    ``<answered>`` is itself a valid objection / reply label; the parsed
    ``answered`` field carries that target (design §6 "and only that one").

    Raises :class:`ValueError` for an empty, malformed, or unknown label, or
    for a magnitude label whose ``:{n}`` part is missing or non-numeric —
    Phase 3a never silently mistypes a label, and the HEURISTIC §5 rows
    (Phase 5) are unknown to this parser and so are rejected.
    """
    if not label:
        raise ValueError("empty witness label")

    # A keyed defense label: ``<defense-type>@<answered-label>``.
    if _DEFENSE_KEY_SEP in label:
        defense_type, _, answered_label = label.partition(_DEFENSE_KEY_SEP)
        defense_fixed = _FIXED.get(defense_type)
        if defense_fixed is None or not defense_type.startswith("defense:"):
            raise ValueError(f"unknown keyed defense label {label!r}")
        if not answered_label:
            raise ValueError(
                f"keyed defense label {label!r} has an empty answered target"
            )
        # The answered target must itself be a valid objection / reply label.
        answered = to_argument_evidence(answered_label)
        if not (
            answered_label.startswith("obj:")
            or answered_label.startswith("reply:")
        ):
            raise ValueError(
                f"keyed defense label {label!r} answers a non-attack label "
                f"{answered_label!r}"
            )
        value, tier = defense_fixed
        return ArgumentEvidence(
            label=label, value=value, tier=tier, answered=answered_label
        )

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
    # ``{n}`` is a material gain/loss magnitude (design §5): a strictly
    # positive base-10 integer of bare ASCII digits. A signed (``-100``,
    # ``+100``) or zero magnitude is malformed — the witness producers only
    # ever emit positive magnitudes, and accepting a signed/zero one would
    # silently mistype a malformed label as valid FACT evidence (cf. the
    # malformed-label rejection above). ``str.isascii() and str.isdecimal()``
    # admits exactly a run of ASCII ``0``-``9`` and rejects empty strings,
    # signs, whitespace, and unicode-digit lookalikes (e.g. ``²``) that would
    # otherwise crash ``int()``.
    if not (tail.isascii() and tail.isdecimal()):
        raise ValueError(
            f"witness label {label!r} has a non-integer magnitude {tail!r}"
        )
    magnitude = int(tail)
    if magnitude <= 0:
        raise ValueError(
            f"witness label {label!r} has a non-positive magnitude {tail!r}"
        )
    value, tier = mag
    return ArgumentEvidence(
        label=label, value=value, tier=tier, magnitude=magnitude
    )
