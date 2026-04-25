from __future__ import annotations

from fastapi import Request

from blunder_tutor.web.config import AuthConfig


def is_https_request(request: Request, auth_config: AuthConfig) -> bool:
    """Return True when the request arrived over TLS — directly or via a
    trusted reverse proxy that terminated TLS and forwarded the scheme in
    ``X-Forwarded-Proto``.

    Consumed by both the HSTS header policy and the session cookie
    Secure-flag computation. Keeping a single source ensures the two track
    the same "TLS hop present?" answer; drift here produces an inconsistent
    security posture (cookie without ``Secure`` but HSTS set, or vice versa).

    ``AUTH_TRUST_PROXY`` gates ``X-Forwarded-Proto`` for the same reason it
    gates ``X-Forwarded-For`` in the rate limiter: a direct-to-uvicorn deploy
    that trusted the header would let any client claim the request was HTTPS
    by setting the header itself.
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
