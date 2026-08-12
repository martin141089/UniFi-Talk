"""Runs the reconciler's `run_once()` on a fixed interval using APScheduler."""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from talkanchor.core.reconciler import Reconciler

logger = logging.getLogger("talkanchor.scheduler")


class PollingScheduler:
    def __init__(self, reconciler: Reconciler, *, interval_seconds: int) -> None:
        self._reconciler = reconciler
        self._interval_seconds = interval_seconds
        self._scheduler = AsyncIOScheduler()

    async def _tick(self) -> None:
        try:
            await self._reconciler.run_once()
        except Exception:
            logger.exception("Unhandled error during reconcile cycle")

    def start(self) -> None:
        self._scheduler.add_job(
            self._tick,
            "interval",
            seconds=self._interval_seconds,
            next_run_time=None,  # first run is triggered explicitly by caller via run_once_now()
            id="talkanchor-poll",
        )
        self._scheduler.start()

    async def run_once_now(self) -> None:
        await self._tick()

    def shutdown(self) -> None:
        self._scheduler.shutdown(wait=False)
