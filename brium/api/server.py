from __future__ import annotations

import os
import re
import time
from collections import defaultdict
from threading import Thread

from flask import Flask, request, jsonify, send_from_directory

from brium.config import Config
from brium.crawler.spider import Crawler, Page
from brium.algorithm.seeds import for_query, DEFAULT_HOMEPAGES
from brium.indexer.indexer import Indexer
from brium.search.engine import SearchEngine

app = Flask(__name__)

_cfg: Config | None = None
_indexer: Indexer | None = None
_engine: SearchEngine | None = None
_crawl_thread: Thread | None = None
_crawl_status: dict = {"running": False, "pages": 0, "error": ""}
_auto_seeds: set[str] = set()

_auto_cooldown: dict[str, float] = {}
_COOLDOWN_SECONDS = 60

_crawl_rate: defaultdict[str, list[float]] = defaultdict(list)
_RATE_LIMIT = 3
_RATE_WINDOW = 60

_URL_RE = re.compile(r"^https?://[^\s/$.?#][^\s]*$", re.IGNORECASE)
_SEEN_QUERIES: set[str] = set()


def init(config: Config):
    global _cfg, _indexer, _engine
    _cfg = config
    _indexer = Indexer(config.index_db)
    _engine = SearchEngine(config.index_db)


static_dir = os.path.join(os.path.dirname(__file__), "static")


def _valid_url(url: str) -> bool:
    return bool(_URL_RE.match(url)) and len(url) < 2048


def _rate_limited(ip: str) -> bool:
    now = time.time()
    ts_list = _crawl_rate[ip]
    ts_list[:] = [t for t in ts_list if now - t < _RATE_WINDOW]
    if len(ts_list) >= _RATE_LIMIT:
        return True
    ts_list.append(now)
    return False


def _do_crawl(seeds: list[str], max_pages: int):
    if _crawl_status["running"]:
        return
    _crawl_status["running"] = True
    _crawl_status["pages"] = 0
    _crawl_status["error"] = ""
    try:
        crawler = Crawler(_cfg, on_page=_on_page)
        crawler.seed(seeds)
        count = crawler.crawl(max_pages)
        _crawl_status["pages"] = count
        crawler.close()
    except Exception as e:
        _crawl_status["error"] = str(e)
    finally:
        _crawl_status["running"] = False


def _on_page(page: Page):
    _indexer.add_page(page)
    _auto_seeds.add(page.url)


@app.route("/")
def index():
    return send_from_directory(static_dir, "index.html")


@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    top_k = int(request.args.get("top_k", 20))
    if not q:
        return jsonify({"error": "missing q param"}), 400

    results = _engine.search(q, min(top_k, 100))
    results_dicts = [r.__dict__ for r in results]

    now = time.time()
    last = _auto_cooldown.get(q, 0)
    low_results = len(results_dicts) < 5 or _indexer.doc_count() < 20
    never_seen = q not in _SEEN_QUERIES
    _SEEN_QUERIES.add(q)

    if never_seen and not _crawl_status["running"] and (now - last) > _COOLDOWN_SECONDS:
        _auto_cooldown[q] = now
        seeds = for_query(q)
        new_seeds = [s for s in seeds if s not in _auto_seeds and _valid_url(s)]
        if new_seeds:
            for s in new_seeds:
                _auto_seeds.add(s)
            max_pages = max(10, min(30, 50 - _indexer.doc_count()))
            Thread(target=_do_crawl, args=(new_seeds, max_pages), daemon=True).start()

    return jsonify({
        "results": results_dicts,
        "total": len(results_dicts),
        "query": q,
        "crawling": _crawl_status["running"],
    })


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

    if _crawl_status["running"]:
        return jsonify({"error": "crawl already running"}), 409

    Thread(target=_do_crawl, args=(seeds, max_pages), daemon=True).start()
    return jsonify({"message": "crawl started", "seeds": seeds, "max_pages": max_pages})
