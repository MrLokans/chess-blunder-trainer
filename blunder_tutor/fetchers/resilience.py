from __future__ import annotations

from http import HTTPStatus

import httpx
from hyx.retry import jitters, retry
from hyx.retry.backoffs import expo

# Backoff cap: 30 s is the upstream rate-limit window for both Lichess
# and chess.com — retrying past it doesn't help.
_MAX_BACKOFF_SECONDS = 30


class RetryableHTTPError(Exception):
    """Raised for HTTP errors that should be retried (5xx, 429)."""

    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        super().__init__(f"HTTP {response.status_code}")


RETRYABLE_EXCEPTIONS = (httpx.TransportError, RetryableHTTPError)


def _is_retryable_status(status_code: int) -> bool:
    return (
        status_code >= HTTPStatus.INTERNAL_SERVER_ERROR
        or status_code == HTTPStatus.TOO_MANY_REQUESTS
    )


@retry(
    on=RETRYABLE_EXCEPTIONS,
    attempts=3,  # 3 retries after initial attempt = 4 total
    backoff=expo(
        min_delay_secs=1,
        max_delay_secs=_MAX_BACKOFF_SECONDS,
        base=2,
        jitter=jitters.full,
    ),
)
async def fetch_with_retry(
    client: httpx.AsyncClient,
    url: str,
    **kwargs,
) -> httpx.Response:
    response = await client.get(url, **kwargs)

    if response.status_code >= HTTPStatus.BAD_REQUEST:
        if _is_retryable_status(response.status_code):
            raise RetryableHTTPError(response)
        response.raise_for_status()

    return response
