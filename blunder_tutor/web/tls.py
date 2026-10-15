from __future__ import annotations

from fastapi import Request

from blunder_tutor.web.config import AuthConfig


def is_https_request(request: Request, auth_config: AuthConfig) -> bool:
    """True if the request arrived over TLS, directly or via a trusted proxy's
    `X-Forwarded-Proto`.

    Single source for HSTS and cookie `Secure` so they cannot disagree. Gated by
    `AUTH_TRUST_PROXY`, as for `X-Forwarded-For`, so a direct client cannot claim HTTPS.
    """
    if request.url.scheme == "https":
        return True
    if auth_config.trust_proxy:
        forwarded = request.headers.get("x-forwarded-proto", "")
        # Header may be a comma-separated chain; the leftmost value is the
        # original client's scheme when the proxy appends.
        if forwarded.split(",", 1)[0].strip().lower() == "https":
            return True
    return False
