from __future__ import annotations

import json
import re
from pathlib import Path
from types import MappingProxyType


# CLDR plural rules for supported locales. The integer literals
# (11, 12, 14, 100, etc.) are CLDR-spec values that encode language-specific
# pluralization boundaries; they are not magic numbers in the WPS sense.
# https://cldr.unicode.org/index/cldr-spec/plural-rules
def _east_slavic_plural(n: int) -> str:
    # CLDR rules for Russian, Ukrainian, Belarusian (identical structure).
    if n % 10 == 1 and n % 100 != 11:  # noqa: WPS432
        return "one"  # noqa: WPS226 — CLDR plural-category names (spec-defined contract with locale JSON).
    if 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):  # noqa: WPS432
        return "few"
    if n % 10 == 0 or 5 <= n % 10 <= 9 or 11 <= n % 100 <= 14:  # noqa: WPS432
        return "many"
    return "other"  # noqa: WPS226 — CLDR plural-category names (spec-defined contract with locale JSON).


def _polish_plural(n: int) -> str:
    if n == 1:
        return "one"
    if 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):  # noqa: WPS432
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
    def replace_plural(match: re.Match) -> str:
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
    def replace_placeholder(match: re.Match) -> str:
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

    def _load_all(self) -> None:
        if not self._locales_dir.exists():
            return
        for path in sorted(self._locales_dir.glob("*.json")):
            locale = path.stem
            with open(path, encoding="utf-8") as f:
                self._translations[locale] = json.load(f)

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
