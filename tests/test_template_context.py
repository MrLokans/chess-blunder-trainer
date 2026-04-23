from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from httpx import ASGITransport

from blunder_tutor.web.middleware import LocaleMiddleware
from blunder_tutor.web.template_context import (
    LOCALE_DISPLAY_NAMES,
    i18n_context,
)


class TestI18nContextProcessor:
    def test_reads_from_request_state(self):
        state = SimpleNamespace(
            t=lambda key, **_: f"t:{key}",
            locale="ru",
            translations_json='{"hello":"привет"}',
            features={"trainer.tactics": True, "dashboard.traps": False},
            features_json='{"trainer.tactics":true,"dashboard.traps":false}',
        )
        request = SimpleNamespace(state=state)

        ctx = i18n_context(request)  # type: ignore[arg-type]

        assert ctx["t"]("nav.trainer") == "t:nav.trainer"
        assert ctx["locale"] == "ru"
        assert ctx["features"] == {
            "trainer.tactics": True,
            "dashboard.traps": False,
        }
        assert ctx["has_feature"]("trainer.tactics") is True
        assert ctx["has_feature"]("dashboard.traps") is False
        assert ctx["has_feature"]("missing.feature") is False
        assert ctx["translations_json"] == '{"hello":"привет"}'
        assert ctx["features_json"] == (
            '{"trainer.tactics":true,"dashboard.traps":false}'
        )
        assert ctx["locale_display_names"] is LOCALE_DISPLAY_NAMES

    def test_falls_back_to_safe_defaults_on_missing_state(self):
        request = SimpleNamespace(state=SimpleNamespace())

        ctx = i18n_context(request)  # type: ignore[arg-type]

        assert ctx["t"]("x") == "x"
        assert ctx["locale"] == "en"
        assert ctx["features"] == {}
        assert ctx["translations_json"] == "{}"
        assert ctx["features_json"] == "{}"


def _build_concurrent_app(tmp_path, features_by_path):
    """FastAPI app whose `_load_features` returns a different map depending
    on request path, with a deliberate `asyncio.sleep` in the middle to
    force interleaving between two concurrent requests.
    """
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "probe.html").write_text(
        '{"features": {{ features_json|safe }}, "locale": "{{ locale }}"}'
    )

    templates = Jinja2Templates(
        directory=str(templates_dir),
        context_processors=[i18n_context],
    )

    app = FastAPI()
    app.state.templates = templates
    app.state.i18n = None  # no translation manager → LocaleMiddleware uses
    # its fallback `t = lambda key: key` path
    # `credentials` mode with no per-request user context makes
    # `_db_path_for` return `None`, skipping the DB-backed locale lookup
    # so the test doesn't need a real settings DB.
    app.state.auth_mode = "credentials"

    class _PatchedLocaleMiddleware(LocaleMiddleware):
        async def _load_features(self, request):
            # Sleep to guarantee the event loop yields between request A
            # writing its features to `request.state` and rendering the
            # template. Without C1's fix, a concurrent request B would
            # race in during this window and clobber the shared state.
            await asyncio.sleep(0.05)
            return features_by_path[request.url.path]

    app.add_middleware(_PatchedLocaleMiddleware)

    @app.get("/a")
    async def _route_a(request: Request):
        return templates.TemplateResponse(request, "probe.html")

    @app.get("/b")
    async def _route_b(request: Request):
        return templates.TemplateResponse(request, "probe.html")

    return app


@pytest.mark.asyncio
async def test_concurrent_requests_see_own_features(tmp_path):
    features_a = {"trainer.tactics": True, "dashboard.traps": False}
    features_b = {"trainer.tactics": False, "dashboard.traps": True}
    app = _build_concurrent_app(tmp_path, {"/a": features_a, "/b": features_b})

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Fire many concurrent A/B pairs; without the C1 fix one side's
        # features leaks into the other's render at least once under the
        # forced sleep window.
        for _ in range(10):
            resp_a, resp_b = await asyncio.gather(
                client.get("/a"), client.get("/b")
            )
            parsed_a = json.loads(resp_a.text)
            parsed_b = json.loads(resp_b.text)
            assert parsed_a["features"] == features_a, parsed_a
            assert parsed_b["features"] == features_b, parsed_b
