from __future__ import annotations

from sentry_sdk.scrubber import DEFAULT_DENYLIST, EventScrubber

from blunder_tutor.auth.fastapi import SESSION_COOKIE_NAME

# Project-specific keys to scrub on top of Sentry's default denylist.
# Defaults already cover password/passwd/secret/api_key/auth/token/etc.
PROJECT_DENYLIST: tuple[str, ...] = (
    "secret_key",
    "invite_code",
    "csrf_token",
    SESSION_COOKIE_NAME,
)


def make_event_scrubber() -> EventScrubber:
    return EventScrubber(
        denylist=[*DEFAULT_DENYLIST, *PROJECT_DENYLIST],
        recursive=True,
    )
