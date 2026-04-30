USER_AGENT = "blunder-tutor/1.0 (https://github.com/blunder-tutor)"


class RateLimitError(Exception):
    """Raised when an upstream provider persistently rate-limits a request.

    Carries the platform name so callers (validation endpoint, sync runner)
    can surface a useful signal without inspecting HTTP internals.
    """

    def __init__(self, platform: str, message: str | None = None) -> None:
        self.platform = platform
        super().__init__(message or f"{platform} rate-limited the request")
