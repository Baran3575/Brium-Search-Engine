from __future__ import annotations

import logging
import time
from threading import Thread, Event

from brium.queue.engine import Queue, Task

log = logging.getLogger(__name__)


class WorkerPool:
    def __init__(self, queue: Queue, num_workers: int = 2):
        self.queue = queue
        self.num_workers = num_workers
        self._workers: list[Thread] = []
        self._stop = Event()
        self._handlers: dict[str, callable] = {}

    def register(self, task_type: str, handler: callable):
        self._handlers[task_type] = handler

    def start(self):
        self._stop.clear()
        for i in range(self.num_workers):
            t = Thread(target=self._worker_loop, args=(i,), daemon=True)
            self._workers.append(t)
            t.start()
        log.info("worker pool started with %d workers", self.num_workers)

    def stop(self, timeout: float = 5.0):
        self._stop.set()
        for t in self._workers:
            t.join(timeout=timeout)
        self._workers.clear()
        log.info("worker pool stopped")

    def _worker_loop(self, worker_id: int):
        while not self._stop.is_set():
            task = self.queue.dequeue(list(self._handlers.keys())) if self._handlers else None
            if task is None:
                self._stop.wait(1)
                continue
            handler = self._handlers.get(task.task_type)
            if handler is None:
                self.queue.fail(task.id, f"no handler for {task.task_type}")
                continue
            try:
                handler(task.payload)
                self.queue.complete(task.id)
            except Exception as e:
                log.warning("worker %d failed task %d (%s): %s",
                            worker_id, task.id, task.task_type, e)
                payload = dict(task.payload)
                payload["retries"] = payload.get("retries", 0) + 1
                self.queue.fail(task.id, str(e))
