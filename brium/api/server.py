from __future__ import annotations

import json
import os
import re
import time
from collections import defaultdict
from threading import Thread

from flask import Flask, request, jsonify

from brium.base.config import Config
from brium.base.types import Page
from brium.crawl.spider import Crawler
from brium.discovery.seeds import for_query
from brium.discovery.wikipedia import set_cache as set_wiki_cache
from brium.discovery.rss import set_cache as set_rss_cache
from brium.cache.engine import Cache
from brium.metrics.engine import Metrics
from brium.queue.engine import Task, Queue
from brium.queue.pool import WorkerPool
from brium.storage.sqlite_backend import SQLiteBackend
from brium.index.engine import Indexer
from brium.search.engine import SearchEngine
from brium.jobs.scheduler import Scheduler
from brium.jobs.tasks import (
    get_rss_refresh_job, get_cache_cleanup_job, get_index_optimize_job,
)

_URL_RE = re.compile(r"^https?://[^\s/$.?#][^\s]*$", re.IGNORECASE)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(__name__)
    return app


class AppState:
    def __init__(self):
        self.cfg: Config | None = None
        self.storage: SQLiteBackend | None = None
        self.indexer: Indexer | None = None
        self.engine: SearchEngine | None = None
        self.cache: Cache | None = None
        self.metrics: Metrics | None = None
        self.queue: Queue | None = None
        self.worker_pool: WorkerPool | None = None
        self.scheduler: Scheduler | None = None
        self.crawl_status: dict = {"running": False, "pages": 0, "error": ""}
        self.auto_seeds: set[str] = set()
        self.auto_cooldown: dict[str, float] = {}
        self.seen_queries: set[str] = set()
        self.crawl_rate: defaultdict[str, list[float]] = defaultdict(list)

    @property
    def cooldown_seconds(self) -> int:
        return 60

    @property
    def rate_limit(self) -> int:
        return 3

    @property
    def rate_window(self) -> int:
        return 60


def init_app(app: Flask, config: Config, with_scheduler: bool = True,
             with_queue: bool = False, ranker_name: str = "bm25") -> AppState:
    state = AppState()
    state.cfg = config

    # Storage
    state.storage = SQLiteBackend(config.index_db)

    # Indexer & SearchEngine sharing the same storage
    state.indexer = Indexer(storage=state.storage)
    state.engine = SearchEngine(storage=state.storage, ranker_name=ranker_name)

    # Cache
    state.cache = Cache(os.path.join(config.data_dir, "cache.db"))

    # Metrics
    state.metrics = Metrics(os.path.join(config.data_dir, "metrics.db"))

    # Queue
    state.queue = Queue(os.path.join(config.data_dir, "queue.db"))

    # Wire cache into discovery modules
    set_wiki_cache(state.cache)
    set_rss_cache(state.cache)

    def _on_page(page: Page):
        state.indexer.add_page(page)
        state.auto_seeds.add(page.url)

    def _do_crawl(seeds: list[str], max_pages: int):
        if state.crawl_status["running"]:
            return
        state.crawl_status["running"] = True
        state.crawl_status["pages"] = 0
        state.crawl_status["error"] = ""
        try:
            crawler = Crawler(config, on_page=_on_page)
            crawler.seed(seeds)
            t0 = time.time()
            count = crawler.crawl(max_pages)
            elapsed = time.time() - t0
            state.crawl_status["pages"] = count
            if state.metrics:
                state.metrics.incr("pages_crawled", count)
                state.metrics.gauge("index_size", state.indexer.doc_count())
                if count > 0:
                    state.metrics.record_latency("crawl_page", elapsed / count)
            crawler.close()
        except Exception as e:
            state.crawl_status["error"] = str(e)
            if state.metrics:
                state.metrics.incr("crawl_errors")
        finally:
            state.crawl_status["running"] = False

    def _queue_crawl_handler(payload: dict):
        seeds = payload.get("seeds", [])
        max_pages = payload.get("max_pages", 10)
        _do_crawl(seeds, max_pages)

    if with_queue:
        state.worker_pool = WorkerPool(state.queue, num_workers=2)
        state.worker_pool.register("crawl", _queue_crawl_handler)
        state.worker_pool.start()

    if with_scheduler:
        state.scheduler = Scheduler()
        state.scheduler.add(get_rss_refresh_job(state.cache))
        state.scheduler.add(get_cache_cleanup_job(state.cache))
        state.scheduler.add(get_index_optimize_job(state.indexer))
        state.scheduler.start()

    def _valid_url(url: str) -> bool:
        return bool(_URL_RE.match(url)) and len(url) < 2048

    def _rate_limited(ip: str) -> bool:
        now = time.time()
        ts_list = state.crawl_rate[ip]
        ts_list[:] = [t for t in ts_list if now - t < state.rate_window]
        if len(ts_list) >= state.rate_limit:
            return True
        ts_list.append(now)
        return False

    @app.route("/search")
    def search():
        q = request.args.get("q", "").strip()
        top_k = int(request.args.get("top_k", 20))
        if not q:
            if state.metrics:
                state.metrics.incr("search_errors")
            return jsonify({"error": "missing q param"}), 400

        t0 = time.time()

        if state.cache:
            cache_key = f"{q}:{top_k}"
            cached = state.cache.get("search", cache_key)
            if cached is not None:
                try:
                    if state.metrics:
                        state.metrics.cache_hit("search")
                        state.metrics.incr("search_count")
                        state.metrics.record_latency("search", time.time() - t0)
                    return jsonify(json.loads(cached))
                except Exception:
                    pass
            if state.metrics:
                state.metrics.cache_miss("search")

        results = state.engine.search(q, min(top_k, 100))
        results_dicts = [r.__dict__ for r in results]
        elapsed = time.time() - t0

        if state.metrics:
            state.metrics.incr("search_count")
            state.metrics.record_latency("search", elapsed)
            state.metrics.gauge("index_size", state.indexer.doc_count())

        now = time.time()
        last = state.auto_cooldown.get(q, 0)
        never_seen = q not in state.seen_queries
        state.seen_queries.add(q)

        if never_seen and not state.crawl_status["running"] and (now - last) > state.cooldown_seconds:
            state.auto_cooldown[q] = now
            seeds = for_query(q)
            new_seeds = [s for s in seeds if s not in state.auto_seeds and _valid_url(s)]
            if new_seeds:
                for s in new_seeds:
                    state.auto_seeds.add(s)
                max_pages = max(10, min(30, 50 - state.indexer.doc_count()))
                # Use queue if available, otherwise direct thread
                if state.queue and state.worker_pool:
                    state.queue.enqueue("crawl", {
                        "seeds": new_seeds,
                        "max_pages": max_pages,
                    })
                else:
                    Thread(target=_do_crawl, args=(new_seeds, max_pages), daemon=True).start()

        response = {
            "results": results_dicts,
            "total": len(results_dicts),
            "query": q,
            "crawling": state.crawl_status["running"],
        }

        if state.cache and results_dicts:
            state.cache.set("search", f"{q}:{top_k}", json.dumps(response), ttl_seconds=300)

        return jsonify(response)

    @app.route("/crawl", methods=["POST"])
    def crawl():
        ip = request.remote_addr or "unknown"
        if _rate_limited(ip):
            return jsonify({"error": "rate limited"}), 429

        body = request.get_json(force=True)
        seeds = body.get("seeds", [])
        max_pages = min(int(body.get("max_pages", 100)), 500)

        if not seeds or not isinstance(seeds, list):
            return jsonify({"error": "seeds must be a non-empty list"}), 400
        for s in seeds:
            if not isinstance(s, str) or not _valid_url(s):
                return jsonify({"error": f"invalid URL: {s}"}), 400

        if state.crawl_status["running"]:
            return jsonify({"error": "crawl already running"}), 409

        if state.queue and state.worker_pool:
            state.queue.enqueue("crawl", {"seeds": seeds, "max_pages": max_pages})
            return jsonify({"message": "crawl queued", "seeds": seeds, "max_pages": max_pages})
        else:
            Thread(target=_do_crawl, args=(seeds, max_pages), daemon=True).start()
            return jsonify({"message": "crawl started", "seeds": seeds, "max_pages": max_pages})

    @app.route("/cache/clear", methods=["POST"])
    def clear_cache():
        if state.cache:
            state.cache.clear_expired()
            return jsonify({"message": "cache cleared"})
        return jsonify({"message": "no cache"}), 200

    @app.route("/metrics")
    def metrics_endpoint():
        if state.metrics:
            snap = state.metrics.snapshot()
            snap["queue"] = {
                "pending": state.queue.pending_count() if state.queue else 0,
            }
            return jsonify(snap)
        return jsonify({"error": "metrics not available"}), 200

    @app.route("/status")
    def status():
        doc_count = state.indexer.doc_count() if state.indexer else 0
        snap = state.metrics.snapshot() if state.metrics else {}
        return jsonify({
            "docs": doc_count,
            "crawling": state.crawl_status["running"],
            "pages_crawled": state.crawl_status["pages"],
            "scheduler_running": state.scheduler is not None,
            "worker_pool_running": state.worker_pool is not None,
            "cache_available": state.cache is not None,
            "metrics_available": state.metrics is not None,
            "queue_pending": state.queue.pending_count() if state.queue else 0,
            "cache_hit_ratio": snap.get("cache", {}).get("hit_ratio", 0),
            "avg_search_latency": snap.get("latency", {}).get("search", 0),
            "rankers": __import__("brium.plugins", fromlist=["Registry"]).Registry.list_rankers(),
            "sources": __import__("brium.plugins", fromlist=["Registry"]).Registry.list_sources(),
            "api_version": __import__("brium.plugins.safe", fromlist=["CURRENT_API_VERSION"]).CURRENT_API_VERSION,
        })

    return state
