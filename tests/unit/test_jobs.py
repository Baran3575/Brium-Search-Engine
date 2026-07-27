from __future__ import annotations

import time

from brium.jobs.scheduler import Scheduler, Job


def test_scheduler_add_job():
    s = Scheduler()
    calls = []

    def my_job():
        calls.append("ran")

    s.add_job("test", 9999, my_job)
    assert len(s._jobs) == 1
    assert s._jobs[0].name == "test"


def test_scheduler_start_stop():
    s = Scheduler()
    s.add_job("test", 9999, lambda: None)
    s.start()
    assert s._thread is not None
    assert s._thread.is_alive()
    s.stop()
    assert s._thread is None


def test_scheduler_run_job():
    s = Scheduler()
    calls = []

    def my_job():
        calls.append("ran")

    s.add_job("test", 0.1, my_job, run_on_start=True)
    s.start()
    time.sleep(0.3)
    s.stop()
    assert len(calls) >= 1


def test_scheduler_job_exception_handling():
    s = Scheduler()
    calls = []

    def failing_job():
        raise ValueError("oops")

    def good_job():
        calls.append("ok")

    s.add_job("fail", 9999, failing_job)
    s.add_job("good", 9999, good_job, run_on_start=True)
    s.start()
    time.sleep(0.2)
    s.stop()
    # The good job should have run despite the failing one
    assert len(calls) >= 1
