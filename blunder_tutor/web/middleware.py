from __future__ import annotations

from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from blunder_tutor.repositories.settings import SettingsRepository


class SetupCheckMiddleware(BaseHTTPMiddleware):
    EXEMPT_PATHS = {"/setup", "/api/", "/health", "/static", "/favicon.ico"}

    async def dispatch(self, request: Request, call_next):
        # Check if path is exempt
        if any(request.url.path.startswith(path) for path in self.EXEMPT_PATHS):
            return await call_next(request)

        # Check if setup is completed (with caching to reduce DB load)
        if not hasattr(request.app.state, "_setup_completed_cache"):
            config = request.app.state.config
            settings_repo = SettingsRepository(db_path=config.data.db_path)
            try:
                request.app.state._setup_completed_cache = (
                    settings_repo.is_setup_completed()
                )
            except Exception:
                # If we can't check setup status, allow the request through
                # (database might be initializing)
                return await call_next(request)

        if not request.app.state._setup_completed_cache:
            return RedirectResponse(url="/setup", status_code=303)

        return await call_next(request)
