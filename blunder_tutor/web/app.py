from __future__ import annotations

import os

from fastapi import FastAPI

from blunder_tutor.web.app_lifecycle import (  # noqa: F401 — `scan_orphans` re-exported for tests/auth/test_account_deletion.py.
    build_app,
    scan_orphans,
)
from blunder_tutor.web.config import AppConfig, config_factory


def create_app(config: AppConfig) -> FastAPI:
    return build_app(config)


def create_app_factory() -> FastAPI:
    """Factory function for uvicorn --factory mode."""
    return create_app(config_factory(None, os.environ))
