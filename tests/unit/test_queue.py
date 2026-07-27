from __future__ import annotations

import os
import tempfile
import time

from brium.queue.engine import Queue, Task


def test_enqueue_dequeue():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "queue.db")
        q = Queue(db)
        tid = q.enqueue("crawl", {"urls": ["http://a.com"]}, priority=1)
        assert tid > 0
        assert q.pending_count() == 1
        task = q.dequeue()
        assert task is not None
        assert task.task_type == "crawl"
        assert task.payload["urls"] == ["http://a.com"]
        assert task.status == "running"
        q.close()


def test_complete_and_fail():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "queue.db")
        q = Queue(db)
        tid = q.enqueue("crawl", {})
        task = q.dequeue()
        q.complete(task.id)
        assert q.pending_count() == 0
        tid2 = q.enqueue("index", {})
        task2 = q.dequeue(["index"])
        q.fail(task2.id, "something broke")
        assert q.pending_count() == 0
        assert q.size("failed") == 1
        q.close()


def test_dequeue_empty():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "queue.db")
        q = Queue(db)
        assert q.dequeue() is None
        assert q.dequeue(["crawl"]) is None
        q.close()


def test_retry_failed():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "queue.db")
        q = Queue(db)
        tid = q.enqueue("crawl", {})
        task = q.dequeue()
        q.fail(task.id, "error")
        assert q.pending_count() == 0
        retried = q.retry_failed(max_retries=3)
        assert retried >= 1
        assert q.pending_count() >= 1
        q.close()


def test_task_types_filter():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "queue.db")
        q = Queue(db)
        q.enqueue("crawl", {})
        q.enqueue("index", {})
        # Dequeue only crawl tasks
        task = q.dequeue(["crawl"])
        assert task is not None
        assert task.task_type == "crawl"
        q.close()
