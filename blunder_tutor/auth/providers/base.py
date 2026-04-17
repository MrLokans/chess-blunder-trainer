from __future__ import annotations

from typing import Protocol

from blunder_tutor.auth.types import Identity, ProviderName


class AuthProvider(Protocol):
    """Pluggable authentication provider.

    Adding OAuth later means writing a new class that satisfies this
    protocol (new provider name, new credentials shape) and registering
    it with `AuthService`; no service-layer changes required.
    """

    name: ProviderName

    async def authenticate(self, credentials: dict[str, str]) -> Identity | None:
        """Return the matching Identity on success, None on failure."""
        ...

    async def close(self) -> None: ...
