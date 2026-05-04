from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import sentry_sdk
from sentry_sdk.tracing import Span as _SentrySpan

from blunder_tutor.observability import sentry_init


class Span:
    """Public span surface — strictly `set_tag` and `set_data`.

    Thin wrapper around the underlying SDK span so call sites never
    import `sentry_sdk` directly. When telemetry is disabled, the inner
    span is `None` and both methods are silent no-ops.
    """

    __slots__ = ("_inner",)

    def __init__(self, inner: _SentrySpan | None) -> None:
        self._inner = inner

    def set_tag(self, key: str, value: Any) -> None:
        if self._inner is not None:
            self._inner.set_tag(key, value)

    def set_data(self, key: str, value: Any) -> None:
        if self._inner is not None:
            self._inner.set_data(key, value)


@contextmanager
def start_span(name: str, op: str | None = None) -> Iterator[Span]:
    if not sentry_init.active:
        yield Span(None)
        return
    with sentry_sdk.start_span(op=op, name=name) as inner:
        yield Span(inner)
