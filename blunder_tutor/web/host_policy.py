from __future__ import annotations

import ipaddress
import logging

from fastapi import status
from fastapi.responses import PlainTextResponse
from starlette.requests import HTTPConnection
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)


def _is_loopback_or_ip_host(hostname: str | None) -> bool:
    if hostname is None:
        return False
    if hostname.lower().rstrip(".") == "localhost":
        return True
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        return False
    return True


class LocalHostOnlyMiddleware:
    """Default Host policy when `ALLOWED_HOSTS` is unset in no-login mode.

    DNS rebinding needs an attacker-controlled hostname, so `localhost` and IP literals
    (LAN access by IP) stay open while any other name must be listed explicitly."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket"):
            url = HTTPConnection(scope).url
            if not _is_loopback_or_ip_host(url.hostname):
                logger.warning(
                    "Rejected Host %r: add it to ALLOWED_HOSTS to serve this name",
                    url.netloc,
                )
                response = PlainTextResponse(
                    "Invalid host header. Set ALLOWED_HOSTS to serve this hostname.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)
