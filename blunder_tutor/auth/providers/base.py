"""Provider Protocol re-export.

Provider authors import :class:`AuthProvider` from here for ergonomic
discovery; the canonical definition lives in :mod:`auth.core.protocols`
alongside the storage / policy Protocols.
"""

from blunder_tutor.auth.core.protocols import AuthProvider

__all__ = ["AuthProvider"]
