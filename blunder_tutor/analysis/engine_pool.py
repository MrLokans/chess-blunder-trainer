from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Awaitable, Callable
from typing import TypeVar

import chess.engine

from blunder_tutor.constants import (
    DEFAULT_ENGINE_CONCURRENCY,
    DEFAULT_ENGINE_HASH_MB,
    DEFAULT_ENGINE_TASK_TIMEOUT,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _is_alive(engine: chess.engine.UciProtocol) -> bool:
    return not engine.returncode.done()


_SENTINEL = object()


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
            try:
                engine = await self._ensure_alive(engine)
                if self._task_timeout is not None:
                    result = await asyncio.wait_for(
                        fn(engine), timeout=self._task_timeout
                    )
                else:
                    result = await fn(engine)
                if not future.cancelled():
                    future.set_result(result)
            except TimeoutError:
                logger.error(
                    "Task timed out after %ss, killing engine", self._task_timeout
                )
                engine = await self._kill_and_respawn(engine)
                if not future.done():
                    future.set_exception(
                        TimeoutError(
                            f"Engine task timed out after {self._task_timeout}s"
                        )
                    )
            except asyncio.CancelledError:
                if not future.done():
                    future.cancel()
                self._queue.task_done()
                break
            except Exception as exc:
                if not future.cancelled():
                    future.set_exception(exc)
            finally:
                self._queue.task_done()

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
