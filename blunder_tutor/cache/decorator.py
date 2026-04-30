from __future__ import annotations

import dataclasses
import functools
import hashlib
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request
from pydantic import BaseModel

from blunder_tutor.cache.backend import CacheBackend

logger = logging.getLogger(__name__)


@dataclasses.dataclass(slots=True)
class _CacheWrapper:
    value: Any


# Cache key is sha256-hashed and truncated to 32 hex chars (128 bits) — long
# enough to make collisions practically impossible across the cache lifetime
# while keeping keys short for storage backends.
_CACHE_KEY_HEX_LEN = 32

cache_backend: CacheBackend | None = None
default_ttl: int = 300


def set_cache_backend(backend: CacheBackend | None, *, ttl: int = 300) -> None:
    global cache_backend, default_ttl  # noqa: PLW0603 — intentional module-level singleton: cache backend + default TTL are configured once at app boot from `cache/__init__.py`.
    cache_backend = backend
    default_ttl = ttl


def get_cache_backend() -> CacheBackend | None:
    return cache_backend


def resolve_user_key(request: Request) -> str:
    return getattr(request.state, "username", "default")


def _serialize_collection(value: Any) -> str | None:
    if isinstance(value, (str, int, float, bool)):
        return json.dumps(value)
    if isinstance(value, (list, tuple)):
        return json.dumps([_serialize_param(v) for v in value], sort_keys=True)
    if isinstance(value, dict):
        return json.dumps(
            {k: _serialize_param(v) for k, v in sorted(value.items())},
            sort_keys=True,
        )
    return None


def _serialize_param(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, BaseModel):
        return value.model_dump_json()
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return json.dumps(dataclasses.asdict(value), sort_keys=True, default=str)
    serialized = _serialize_collection(value)
    return serialized if serialized is not None else str(value)


def _build_cache_key(
    func: Callable,
    version: int,
    user_key: str,
    key_params: list[str],
    kwargs: dict[str, Any],
) -> str:
    parts = [
        f"v{version}",
        f"{func.__module__}.{func.__qualname__}",
        user_key,
    ]
    for name in sorted(key_params):
        value = kwargs.get(name)
        parts.append(f"{name}={_serialize_param(value)}")

    raw = ":".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:_CACHE_KEY_HEX_LEN]


def _resolve_request(args: tuple[Any, ...], kwargs: dict[str, Any]) -> Request | None:
    request = kwargs.get("request")
    if request is not None:
        return request
    for arg in args:
        if isinstance(arg, Request):
            return arg
    return None


async def _get_or_compute(
    backend: CacheBackend,
    cache_key: str,
    scoped_tag: str,
    ttl: int,
    factory: Callable[[], Awaitable[Any]],
) -> Any:
    cached_entry = await backend.get(cache_key)
    if isinstance(cached_entry, _CacheWrapper):
        return cached_entry.value

    result = await factory()
    await backend.set(cache_key, _CacheWrapper(result), ttl=ttl, tags={scoped_tag})
    return result


def cached(
    *,
    tag: str,
    ttl: int | None = None,
    version: int = 1,
    key_params: list[str],
) -> Callable:
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            backend = get_cache_backend()
            if backend is None:
                return await func(*args, **kwargs)

            request = _resolve_request(args, kwargs)
            user_key = resolve_user_key(request) if request else "default"
            cache_key = _build_cache_key(func, version, user_key, key_params, kwargs)
            scoped_tag = f"{tag}:{user_key}"
            effective_ttl = ttl if ttl is not None else default_ttl

            return await _get_or_compute(
                backend,
                cache_key,
                scoped_tag,
                effective_ttl,
                lambda: func(*args, **kwargs),
            )

        return wrapper

    return decorator
