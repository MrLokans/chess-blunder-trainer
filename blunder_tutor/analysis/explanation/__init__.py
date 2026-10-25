"""Beginner-friendly explanations for blunder puzzles, built as i18n messages.

PV-first: instead of inferring causes from static patterns (which misattributed
causality), walk the engine's principal variation and describe what concretely happens:
captures, net material change, mate.

`generate.generate_explanation` builds one `Puzzle` and asks two ordered chains for a
sentence each: `blunder._BLUNDER_STRATEGIES` (why the played move fails) and
`best._BEST_STRATEGIES` (why the best move is better); the first step that applies wins.

Output is `I18nMessage(key, params)`, never raw text; piece names are passed as i18n key
references so morphologically rich languages can decline them. Keys live under
`explanation.blunder.*` and `explanation.best.*` in `locales/*.json`. Background survey:
docs/explaining-engines.md."""

from blunder_tutor.analysis.explanation.generate import generate_explanation
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
