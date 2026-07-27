from __future__ import annotations

import logging
import time
from threading import Thread, Event
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


@dataclass
class Job:
    name: str
    interval_seconds: float
    fn: callable
    run_on_start: bool = False


class Scheduler:
    def __init__(self):
        self._jobs: list[Job] = []
        self._thread: Thread | None = None
        self._stop = Event()

    def add(self, job: Job):
        self._jobs.append(job)

    def add_job(self, name: str, interval_seconds: float, fn: callable, run_on_start: bool = False):
        self._jobs.append(Job(name, interval_seconds, fn, run_on_start))

    def start(self):
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = Thread(target=self._run, daemon=True)
        self._thread.start()
        log.info("scheduler started with %d jobs", len(self._jobs))

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        log.info("scheduler stopped")

    def _run(self):
        last_run: dict[str, float] = {}
        for job in self._jobs:
            if job.run_on_start:
                self._safe_run(job)
                last_run[job.name] = time.time()
            else:
                last_run[job.name] = 0.0

        while not self._stop.is_set():
            now = time.time()
            for job in self._jobs:
                if now - last_run.get(job.name, 0.0) >= job.interval_seconds:
                    self._safe_run(job)
                    last_run[job.name] = now
            self._stop.wait(15)

    def _safe_run(self, job: Job):
        try:
            log.debug("running job: %s", job.name)
            job.fn()
        except Exception:
            log.exception("job failed: %s", job.name)
