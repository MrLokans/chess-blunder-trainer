"""Shared facade-call capture helper for instrumentation smoke tests.

The pattern: monkey-patch the facade-level functions (``count``, ``gauge``,
``distribution``, ``start_span``) as imported into the target module, and
record every invocation. Tests assert on the captured calls. This couples
the tests to the facade contract — exactly the regression we want to catch
— and avoids depending on sentry_sdk transport internals.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from types import ModuleType
from typing import Any
from unittest.mock import MagicMock

import pytest


class FacadeCallRecorder:
    """Record-only stand-ins for the observability facade primitives."""

    def __init__(self) -> None:
        self.spans: list[dict[str, Any]] = []
        self.counts: list[dict[str, Any]] = []
        self.gauges: list[dict[str, Any]] = []
        self.distributions: list[dict[str, Any]] = []
        self.tags: list[tuple[str, Any]] = []
        self.data: list[tuple[str, Any]] = []

        span = MagicMock()
        span.set_tag = lambda k, v: self.tags.append((k, v))
        span.set_data = lambda k, v: self.data.append((k, v))
        self._span = span

    @contextmanager
    def start_span(self, name: str, op: str | None = None) -> Iterator[MagicMock]:
        self.spans.append({"name": name, "op": op})
        yield self._span

    def count(self, name: str, value: float = 1.0, tags: dict | None = None) -> None:
        self.counts.append({"name": name, "value": value, "tags": tags})

    def gauge(self, name: str, value: float, tags: dict | None = None) -> None:
        self.gauges.append({"name": name, "value": value, "tags": tags})

    def distribution(self, name: str, value: float, tags: dict | None = None) -> None:
        self.distributions.append({"name": name, "value": value, "tags": tags})


def patch_facade(
    monkeypatch: pytest.MonkeyPatch,
    target_module: ModuleType,
    *,
    primitives: tuple[str, ...] = ("count", "gauge", "distribution", "start_span"),
) -> FacadeCallRecorder:
    """Monkey-patch the named facade primitives on *target_module* with a
    fresh recorder and return it. Only patches primitives that exist on
    the module (so a module that uses ``count`` / ``gauge`` only does not
    need to import ``start_span``).
    """
    recorder = FacadeCallRecorder()
    for name in primitives:
        if hasattr(target_module, name):
            monkeypatch.setattr(target_module, name, getattr(recorder, name))
    return recorder
