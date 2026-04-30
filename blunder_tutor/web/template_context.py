from __future__ import annotations

from types import MappingProxyType
from typing import Any

from fastapi import Request

LOCALE_DISPLAY_NAMES = MappingProxyType(
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
    """Jinja2Templates context processor.

    All per-request template state (``t``, ``locale``, ``features``, etc.)
    lives on ``request.state`` — set by ``LocaleMiddleware`` — and is pulled
    into the render context here. Historically these values were assigned
    to ``templates.env.globals`` per request, which mutated a
    process-shared dict; under concurrent requests the awaits between
    "globals written" and "template rendered" let one user's map render
    for another. Sourcing from ``request.state`` keeps each render
    strictly scoped to its own request.
    """
    state = request.state
    features: dict[str, bool] = getattr(state, "features", {})
    # `features.get` would return ``None`` for unknown keys, which renders
    # as the string "None" in ``{{ has_feature('x') }}``. Wrap in ``bool``
    # so both absence and explicit ``False`` look the same to a template.
    return {
        "t": getattr(state, "t", _default_t),
        "locale": getattr(state, "locale", "en"),
        "translations_json": getattr(state, "translations_json", "{}"),
        "features": features,
        "has_feature": lambda key: bool(features.get(key, False)),
        "features_json": getattr(state, "features_json", "{}"),
        "locale_display_names": LOCALE_DISPLAY_NAMES,
    }
