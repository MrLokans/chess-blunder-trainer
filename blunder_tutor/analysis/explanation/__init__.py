"""Beginner-friendly explanations for blunder puzzles, built as i18n messages.

PV-first: instead of inferring causes from static patterns (which misattributed
causality), walk the engine's principal variation and describe what concretely happens:
captures, net material change, mate.

`best.explain_best` tries, in order: immediate mate; line analysis (mate in N, sacrifice
combination, multi-move material win; a simple direct capture returns None so the static
layer can word it more concisely); then the static fallback (check + capture, tactical
pattern, undefended capture, pawn damage from the line, retreat, capture, new threat,
centipawn-loss avoidance). The tactical pattern is the best move's own tactic: a puzzle's
stored pattern may describe what the blunder allowed.

`blunder.explain_blunder` is static plus the opponent's refutation: missed mate, piece
landing undefended, exposed piece, ignored threat, bad capture, refutation wins material
or mates, else centipawn loss.

Output is `I18nMessage(key, params)`, never raw text; piece names are passed as i18n key
references so morphologically rich languages can decline them. Keys live under
`explanation.blunder.*` and `explanation.best.*` in `locales/*.json`. Background survey:
docs/explaining-engines.md."""

from blunder_tutor.analysis.explanation.best import generate_explanation
from blunder_tutor.analysis.explanation.messages import (
    BlunderExplanation,
    I18nMessage,
    ResolvedExplanation,
    resolve_explanation,
)

__all__ = [
    "BlunderExplanation",
    "I18nMessage",
    "ResolvedExplanation",
    "generate_explanation",
    "resolve_explanation",
]
