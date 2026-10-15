from dataclasses import dataclass

USER_AGENT = "blunder-tutor/1.0 (https://github.com/blunder-tutor)"


class RateLimitError(Exception):
    def __init__(self, platform: str, message: str | None = None) -> None:
        self.platform = platform
        super().__init__(message or f"{platform} rate-limited the request")


@dataclass(frozen=True)
class ExistenceCheck:
    """`exists` is unreliable (False) when `rate_limited`."""

    exists: bool
    rate_limited: bool
