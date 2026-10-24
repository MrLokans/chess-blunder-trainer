from __future__ import annotations

from typing import Any

from fastapi import Request

LOCALE_DISPLAY_NAMES = frozendict(
    {
        "en": "English",
        "ru": "Русский",
        "uk": "Українська",
        "de": "Deutsch",
        "fr": "Français",
        "es": "Español",
        "pl": "Polski",
        "be": "Беларуская",
        "zh": "中文",
    }
)


def _default_t(key: str, **_: Any) -> str:
    return key


def i18n_context(request: Request) -> dict[str, Any]:
    """Context processor pulling per-request state (`t`, `locale`, `features`, ...) from
    `request.state`. Writing it to shared `templates.env.globals` raced under concurrent
    requests and rendered one user's map for another."""
    state = request.state
    features: dict[str, bool] = getattr(state, "features", {})
    # `features.get` returns None, which renders as "None" in templates; `bool` makes
    # absence and False identical.
    return {
        "t": getattr(state, "t", _default_t),
        "locale": getattr(state, "locale", "en"),
        "translations_json": getattr(state, "translations_json", "{}"),
        "features": features,
        "has_feature": lambda key: bool(features.get(key, False)),
        "features_json": getattr(state, "features_json", "{}"),
        "locale_display_names": LOCALE_DISPLAY_NAMES,
    }
