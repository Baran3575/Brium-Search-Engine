from __future__ import annotations

import os
import time
from threading import Thread

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


def init(config: Config):
    global _cfg, _indexer, _engine
    _cfg = config
    _indexer = Indexer(config.index_db)
    _engine = SearchEngine(config.index_db)


static_dir = os.path.join(os.path.dirname(__file__), "static")


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

    if len(results_dicts) < 3 and not _crawl_status["running"]:
        _auto_crawl_for_query(q)

    return jsonify({
        "results": results_dicts,
        "total": len(results_dicts),
        "query": q,
        "crawling": _crawl_status["running"],
    })


def _auto_crawl_for_query(query: str):
    import urllib.parse
    wiki_slug = query.strip().lower().replace(" ", "_")
    seeds = [
        f"https://en.wikipedia.org/wiki/{urllib.parse.quote(wiki_slug)}",
        f"https://en.wikipedia.org/wiki/{urllib.parse.quote(wiki_slug + '_(')}",
    ]
    new_seeds = [s for s in seeds if s not in _auto_seeds]
    if not new_seeds:
        return

    max_pages = max(3, 10 - _indexer.doc_count())

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


@app.route("/crawl", methods=["POST"])
def crawl():
    body = request.get_json(force=True)
    seeds = body.get("seeds", [])
    max_pages = int(body.get("max_pages", 100))
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
