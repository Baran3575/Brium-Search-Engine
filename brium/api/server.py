from __future__ import annotations

import json
from threading import Thread

from flask import Flask, request, jsonify

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


def init(config: Config):
    global _cfg, _indexer, _engine
    _cfg = config
    _indexer = Indexer(config.index_db)
    _engine = SearchEngine(config.index_db)


@app.route("/search")
def search():
    q = request.args.get("q", "")
    top_k = int(request.args.get("top_k", 20))
    if not q:
        return jsonify({"error": "missing q param"}), 400
    results = _engine.search(q, min(top_k, 100))
    return jsonify({
        "results": [r.__dict__ for r in results],
        "total": len(results),
        "query": q,
    })


@app.route("/status")
def status():
    return jsonify({
        "docs_indexed": _indexer.doc_count(),
        "total_terms": _indexer.total_terms(),
        "crawl_running": _crawl_status["running"],
        "crawl_pages": _crawl_status["pages"],
    })


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
