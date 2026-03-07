from __future__ import annotations

import asyncio
import logging
import time

from .poller import Poller


class PollScheduler:
    def __init__(self, poller: Poller, interval: int) -> None:
        self.poller = poller
        self.interval = interval
        self.logger = logging.getLogger(self.__class__.__name__)
        self._stop_event = asyncio.Event()

    def stop(self) -> None:
        self._stop_event.set()

    async def run_forever(self) -> None:
        self.logger.info("scheduler started (interval=%ss)", self.interval)
        while not self._stop_event.is_set():
            started = time.monotonic()
            try:
                await self.poller.poll_once()
            except Exception:
                self.logger.exception("unexpected error in polling cycle")

            elapsed = time.monotonic() - started
            sleep_seconds = max(1, int(self.interval - elapsed))
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=sleep_seconds)
            except asyncio.TimeoutError:
                pass

        self.logger.info("scheduler stopped")
