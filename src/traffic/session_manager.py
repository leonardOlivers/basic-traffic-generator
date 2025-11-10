thonfrom __future__ import annotations

import asyncio
import logging
from typing import Optional

from asyncio import QueueEmpty as AsyncQueueEmpty

from storage.queue_handler import URLQueue  # type: ignore
from storage.dataset_writer import DatasetWriter  # type: ignore
from traffic.browser_driver import BrowserDriver  # type: ignore
from traffic.action_simulator import ActionSimulator  # type: ignore

class SessionManager:
    def __init__(
        self,
        browser_driver: BrowserDriver,
        url_queue: URLQueue,
        writer: DatasetWriter,
        max_interactions: int,
        concurrency: int,
        delay_between_sessions: float = 0.0,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.browser_driver = browser_driver
        self.url_queue = url_queue
        self.writer = writer
        self.max_interactions = max_interactions
        self.concurrency = max(1, concurrency)
        self.delay_between_sessions = max(0.0, delay_between_sessions)
        self.logger = logger or logging.getLogger("session-manager")
        self.action_simulator = ActionSimulator(logger=self.logger)

    async def _worker(self, worker_id: int) -> None:
        self.logger.info("Worker %d started.", worker_id)
        while True:
            try:
                url = self.url_queue.get_nowait()
            except AsyncQueueEmpty:
                self.logger.info("Worker %d exiting (queue empty).", worker_id)
                break

            try:
                context, page = await self.browser_driver.new_page()
                try:
                    self.logger.info("Worker %d visiting: %s", worker_id, url)
                    record = await self.action_simulator.simulate(
                        page, url, max_interactions=self.max_interactions
                    )
                    self.writer.add_record(record)
                    self.logger.info(
                        "Worker %d completed: %s | status=%s | time=%s",
                        worker_id,
                        url,
                        record["status_code"],
                        record["response_time"],
                    )
                finally:
                    await context.close()
            except Exception as exc:
                self.logger.error("Worker %d encountered an error on %s: %s", worker_id, url, exc)
            finally:
                self.url_queue.task_done()
                if self.delay_between_sessions:
                    await asyncio.sleep(self.delay_between_sessions)

    async def run(self) -> None:
        self.logger.info("Starting session manager with concurrency=%d.", self.concurrency)
        workers = [asyncio.create_task(self._worker(worker_id=i)) for i in range(self.concurrency)]
        await asyncio.gather(*workers)
        self.logger.info("All workers completed.")