from __future__ import annotations

import json
import re
from pathlib import Path
from types import MappingProxyType

# CLDR plural-rule constants. The integer values are CLDR-spec
# pluralization boundaries (https://cldr.unicode.org/index/cldr-spec/plural-rules),
# not arbitrary magic numbers — naming them documents the contract and
# satisfies WPS432.
_LAST_DIGIT_BASE = 10
_LAST_TWO_BASE = 100
_TEEN_LO = 11
_TEEN_HI = 14
_FEW_HI = 4
_MANY_LO = 5
_MANY_HI = 9
_TEEN_FEW_LO = 12


def _east_slavic_plural(n: int) -> str:
    # CLDR rules for Russian, Ukrainian, Belarusian (identical structure).
    last_digit = n % _LAST_DIGIT_BASE
    last_two = n % _LAST_TWO_BASE
    if last_digit == 1 and last_two != _TEEN_LO:
        return "one"  # noqa: WPS226 — CLDR plural-category names (spec-defined contract with locale JSON).
    if 2 <= last_digit <= _FEW_HI and not (_TEEN_FEW_LO <= last_two <= _TEEN_HI):
        return "few"
    if last_digit == 0 or _MANY_LO <= last_digit <= _MANY_HI:
        return "many"
    if _TEEN_LO <= last_two <= _TEEN_HI:
        return "many"
    return "other"  # noqa: WPS226 — CLDR plural-category names (spec-defined contract with locale JSON).


def _polish_plural(n: int) -> str:
    last_digit = n % _LAST_DIGIT_BASE
    last_two = n % _LAST_TWO_BASE
    if n == 1:
        return "one"
    if 2 <= last_digit <= _FEW_HI and not (_TEEN_FEW_LO <= last_two <= _TEEN_HI):
        return "few"
    return "many"


PLURAL_RULES: MappingProxyType = MappingProxyType(
    {
        "en": lambda n: "one" if n == 1 else "other",  # noqa: WPS226 — locale codes and CLDR plural names repeat across rule defs by design.
        "ru": _east_slavic_plural,
        "uk": _east_slavic_plural,
        "de": lambda n: "one" if n == 1 else "other",
        "fr": lambda n: "one" if n in (0, 1) else "other",
        "es": lambda n: "one" if n == 1 else "other",
        "pl": _polish_plural,
        "be": _east_slavic_plural,
        "zh": lambda n: "other",
    }
)

# Matches {varName, plural, one {text} other {text}} patterns
_PLURAL_RE = re.compile(r"\{(\w+),\s*plural,\s*(.*)\}", re.DOTALL)
# Matches individual plural branches like: one {some text} or =0 {some text}
_BRANCH_RE = re.compile(r"(=\d+|\w+)\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}")
# Matches simple {varName} placeholders
_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")


def _resolve_plural(message: str, params: dict[str, object], locale: str) -> str:
    def replace_plural(match: re.Match) -> str:  # noqa: WPS430 — `re.sub` callback; captures `params`/`locale`.
        var_name = match.group(1)
        branches_str = match.group(2)
        count = params.get(var_name, 0)
        if not isinstance(count, int | float):
            try:
                count = int(count)
            except (ValueError, TypeError):
                count = 0

        branches = {}
        for branch_match in _BRANCH_RE.finditer(branches_str):
            category = branch_match.group(1)
            text = branch_match.group(2)
            branches[category] = text

        # Check for exact match first (=0, =1, etc.)
        exact_match = branches.get(f"={int(count)}")
        if exact_match is not None:
            result = exact_match
        else:
            rule = PLURAL_RULES.get(locale, PLURAL_RULES["en"])
            category = rule(int(count))
            result = branches.get(category, branches.get("other", ""))

        return result.replace("#", str(count))

    return _PLURAL_RE.sub(replace_plural, message)


def _resolve_placeholders(message: str, params: dict[str, object]) -> str:
    def replace_placeholder(match: re.Match) -> str:  # noqa: WPS430 — `re.sub` callback; captures `params`.
        key = match.group(1)
        return str(params.get(key, match.group(0)))

    return _PLACEHOLDER_RE.sub(replace_placeholder, message)


def format_message(
    message: str, params: dict[str, object] | None = None, locale: str = "en"
) -> str:
    if not params:
        return message
    result = _resolve_plural(message, params, locale)
    result = _resolve_placeholders(result, params)
    return result


class TranslationManager:
    def __init__(self, locales_dir: str | Path) -> None:
        self._locales_dir = Path(locales_dir)
        self._translations: dict[str, dict[str, str]] = {}
        self._load_all()

    def t(self, locale: str, key: str, **params: object) -> str:
        message = self._translations.get(locale, {}).get(key)
        if message is None:
            message = self._translations.get("en", {}).get(key)
        if message is None:
            return key
        return format_message(message, params if params else None, locale)

    def get_all(self, locale: str) -> dict[str, str]:
        base = dict(self._translations.get("en", {}))
        if locale != "en":
            base.update(self._translations.get(locale, {}))
        return base

    def available_locales(self) -> list[str]:
        return sorted(self._translations.keys())

    def reload(self) -> None:
        self._translations.clear()
        self._load_all()

    def _load_all(self) -> None:
        if not self._locales_dir.exists():
            return
        for path in sorted(self._locales_dir.glob("*.json")):
            locale = path.stem
            with open(path, encoding="utf-8") as f:
                self._translations[locale] = json.load(f)
