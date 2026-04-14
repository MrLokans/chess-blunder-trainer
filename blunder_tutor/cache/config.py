from __future__ import annotations

from pydantic import BaseModel


class CacheConfig(BaseModel):
    enabled: bool = True
    default_ttl: int = 300
