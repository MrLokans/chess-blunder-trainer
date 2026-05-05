from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Awaitable, Callable
from time import monotonic
from typing import Any, TypeVar

import chess.engine

from blunder_tutor.constants import (
    DEFAULT_ENGINE_CONCURRENCY,
    DEFAULT_ENGINE_HASH_MB,
    DEFAULT_ENGINE_TASK_TIMEOUT,
)
from blunder_tutor.observability import count, distribution, start_span

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _is_alive(engine: chess.engine.UciProtocol) -> bool:
    return not engine.returncode.done()


_SENTINEL = object()


def _emit_engine_telemetry(outcome: str, elapsed_ms: float) -> None:
    """Bounded-cardinality contract for the engine chokepoint metrics.

    Both the metric names and the tag schema are part of the operator's
    dashboards (see `docs/conventions/observability.md`). Renaming
    requires updating the conventions doc and any operator-side alerts.
    """
    count("engine.analyse.completed", tags={"outcome": outcome})
    distribution("engine.analyse.duration_ms", elapsed_ms)


class EnginePool:
    def __init__(
        self,
        engine_path: str,
        size: int,
        task_timeout: float | None = DEFAULT_ENGINE_TASK_TIMEOUT,
        threads_per_engine: int | None = None,
        hash_mb: int | None = None,
    ) -> None:
        self._engine_path = engine_path
        self._size = size
        self._task_timeout = task_timeout
        cpu_count = os.cpu_count() or 1
        self._threads_per_engine = threads_per_engine or max(1, cpu_count // size)
        self._hash_mb = hash_mb or DEFAULT_ENGINE_HASH_MB
        self._queue: asyncio.Queue[object] = asyncio.Queue()
        self._engines: list[chess.engine.UciProtocol] = []
        self._workers: list[asyncio.Task] = []
        self._shutting_down = False

    async def start(self) -> None:
        for _ in range(self._size):
            await self._spawn_engine()
        self._workers = [
            asyncio.create_task(self._worker(engine)) for engine in self._engines
        ]
        logger.info("Engine pool started with %d workers", self._size)

    def submit(
        self,
        fn: Callable[[chess.engine.UciProtocol], Awaitable[T]],
    ) -> asyncio.Future[T]:
        future: asyncio.Future[T] = asyncio.get_event_loop().create_future()
        self._queue.put_nowait((fn, future))
        return future

    async def drain(self) -> None:
        await self._queue.join()

    async def shutdown(self) -> None:
        self._shutting_down = True

        for _ in self._workers:
            self._queue.put_nowait(_SENTINEL)

        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()

        for engine in self._engines:
            try:
                if _is_alive(engine):
                    await engine.quit()
            except Exception:
                logger.debug("Engine quit error during shutdown", exc_info=True)
        self._engines.clear()
        logger.info("Engine pool shut down")

    async def _spawn_engine(self) -> chess.engine.UciProtocol:
        _, engine = await chess.engine.popen_uci(self._engine_path)
        options: dict[str, int] = {}
        if "Threads" in engine.options:
            options["Threads"] = self._threads_per_engine
        if "Hash" in engine.options:
            options["Hash"] = self._hash_mb
        if options:
            await engine.configure(options)
        self._engines.append(engine)
        return engine

    async def _ensure_alive(
        self, engine: chess.engine.UciProtocol
    ) -> chess.engine.UciProtocol:
        if _is_alive(engine):
            return engine
        if self._shutting_down:
            raise chess.engine.EngineTerminatedError("pool is shutting down")
        logger.warning("Dead engine detected, spawning replacement")
        if engine in self._engines:
            self._engines.remove(engine)
        return await self._spawn_engine()

    async def _kill_and_respawn(
        self, engine: chess.engine.UciProtocol
    ) -> chess.engine.UciProtocol:
        if engine in self._engines:
            self._engines.remove(engine)
        try:
            engine.kill()
        except Exception:
            logger.debug("Engine kill error", exc_info=True)
        return await self._spawn_engine()

    async def _worker(self, engine: chess.engine.UciProtocol) -> None:
        while True:
            try:
                item = await self._queue.get()
            except asyncio.CancelledError:
                break

            if item is _SENTINEL:
                self._queue.task_done()
                break

            fn, future = item
            engine, should_continue = await self._handle_task(engine, fn, future)
            if not should_continue:
                break

    async def _run_with_optional_timeout(
        self,
        engine: chess.engine.UciProtocol,
        fn: Callable[[chess.engine.UciProtocol], Awaitable[Any]],
    ) -> Any:
        if self._task_timeout is None:
            return await fn(engine)
        return await asyncio.wait_for(fn(engine), timeout=self._task_timeout)

    async def _handle_task(
        self,
        engine: chess.engine.UciProtocol,
        fn: Callable[[chess.engine.UciProtocol], Awaitable[Any]],
        future: asyncio.Future,
    ) -> tuple[chess.engine.UciProtocol, bool]:
        # Exists solely to scope the `engine.analyse` span around
        # `_dispatch_engine_task`. Do not inline — splitting was needed
        # both for span boundary clarity and to keep WPS231 cognitive
        # complexity under the project ceiling.
        with start_span("engine.analyse", op="chess.engine"):
            return await self._dispatch_engine_task(engine, fn, future)

    async def _dispatch_engine_task(
        self,
        engine: chess.engine.UciProtocol,
        fn: Callable[[chess.engine.UciProtocol], Awaitable[Any]],
        future: asyncio.Future,
    ) -> tuple[chess.engine.UciProtocol, bool]:
        outcome = "ok"
        t0 = monotonic()
        try:
            engine = await self._ensure_alive(engine)
            result = await self._run_with_optional_timeout(engine, fn)
            if not future.cancelled():
                future.set_result(result)
        except TimeoutError:
            outcome = "timeout"
            logger.error("Task timed out after %ss, killing engine", self._task_timeout)
            engine = await self._kill_and_respawn(engine)
            if not future.done():
                future.set_exception(
                    TimeoutError(f"Engine task timed out after {self._task_timeout}s")
                )
        except asyncio.CancelledError:
            outcome = "cancelled"
            if not future.done():
                future.cancel()
            return engine, False
        except Exception as exc:
            outcome = "error"
            if not future.cancelled():
                future.set_exception(exc)
        finally:
            self._queue.task_done()
            _emit_engine_telemetry(outcome, (monotonic() - t0) * 1000.0)
        return engine, True


class WorkCoordinator:
    def __init__(
        self,
        engine_path: str,
        pool_size: int | None = None,
        task_timeout: float | None = DEFAULT_ENGINE_TASK_TIMEOUT,
        threads_per_engine: int | None = None,
        hash_mb: int | None = None,
    ) -> None:
        effective_size = pool_size or min(
            DEFAULT_ENGINE_CONCURRENCY, os.cpu_count() or 1
        )
        self._pool = EnginePool(
            engine_path,
            effective_size,
            task_timeout=task_timeout,
            threads_per_engine=threads_per_engine,
            hash_mb=hash_mb,
        )

    async def start(self) -> None:
        await self._pool.start()
        logger.info("WorkCoordinator started")

    def submit(
        self,
        fn: Callable[[chess.engine.UciProtocol], Awaitable[T]],
    ) -> asyncio.Future[T]:
        return self._pool.submit(fn)

    async def drain(self) -> None:
        await self._pool.drain()

    async def shutdown(self) -> None:
        await self._pool.shutdown()
        logger.info("WorkCoordinator shut down")
