"""Env-var parsing helpers shared across config builders."""

from __future__ import annotations

_TRUTHY = frozenset(("true", "1", "yes"))
_FALSY = frozenset(("false", "0", "no"))


def parse_bool(raw: str | None, *, default: bool) -> bool:
    if raw is None or raw == "":
        return default
    low = raw.lower()
    if low in _TRUTHY:
        return True
    if low in _FALSY:
        return False
    raise ValueError(f"expected boolean-like value, got {raw!r}")


def parse_optional_bool(raw: str | None) -> bool | None:
    if raw is None or raw == "":
        return None
    low = raw.lower()
    if low in _TRUTHY:
        return True
    if low in _FALSY:
        return False
    raise ValueError(f"expected boolean-like value, got {raw!r}")
