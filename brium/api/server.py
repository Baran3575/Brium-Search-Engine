from __future__ import annotations

import os
import re
import time
from collections import defaultdict
from threading import Thread
from urllib.parse import urlparse, quote

from flask import Flask, request, jsonify, send_from_directory

from brium.config import Config
from brium.crawler.spider import Crawler, Page
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


def _auto_seeds_for(query: str) -> list[str]:
    slug = query.strip().lower().replace(" ", "_")
    encoded = quote(slug, safe="")
    seeds = [
        f"https://en.wikipedia.org/wiki/{encoded}",
    ]
    for lang in ("tr", "simple", "de", "fr", "es"):
        seeds.append(f"https://{lang}.wikipedia.org/wiki/{encoded}")
    return seeds


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
    if len(results_dicts) < 3 and not _crawl_status["running"] and (now - last) > _COOLDOWN_SECONDS:
        _auto_cooldown[q] = now
        seeds = _auto_seeds_for(q)
        new_seeds = [s for s in seeds if s not in _auto_seeds and _valid_url(s)]
        if new_seeds:
            max_pages = max(3, min(15, 10 - _indexer.doc_count()))

            def _run():
                _crawl_status["running"] = True
                _crawl_status["pages"] = 0
                _crawl_status["error"] = ""
                try:
                    crawler = Crawler(_cfg, on_page=_on_page)
                    crawler.seed(new_seeds)
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

            for s in new_seeds:
                _auto_seeds.add(s)
            global _crawl_thread
            _crawl_thread = Thread(target=_run, daemon=True)
            _crawl_thread.start()

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

    def _run():
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

    global _crawl_thread
    _crawl_thread = Thread(target=_run, daemon=True)
    _crawl_thread.start()
    return jsonify({"message": "crawl started", "seeds": seeds, "max_pages": max_pages})
