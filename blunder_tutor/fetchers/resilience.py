from __future__ import annotations

import httpx
from hyx.retry import jitters, retry
from hyx.retry.backoffs import expo


class RetryableHTTPError(Exception):
    """Raised for HTTP errors that should be retried (5xx, 429)."""

    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        super().__init__(f"HTTP {response.status_code}")


RETRYABLE_EXCEPTIONS = (httpx.TransportError, RetryableHTTPError)


def _is_retryable_status(status_code: int) -> bool:
    return status_code >= 500 or status_code == 429


@retry(
    on=RETRYABLE_EXCEPTIONS,
    attempts=3,  # 3 retries after initial attempt = 4 total
    backoff=expo(
        min_delay_secs=1,
        max_delay_secs=30,
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

    if response.status_code >= 400:
        if _is_retryable_status(response.status_code):
            raise RetryableHTTPError(response)
        response.raise_for_status()

    return response
