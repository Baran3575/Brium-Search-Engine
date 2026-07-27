from __future__ import annotations

import argparse
import logging
import os

from brium.base.config import Config
from brium.crawl.spider import Crawler
from brium.index.engine import Indexer
from brium.search.engine import SearchEngine
from brium.plugins.registry import Registry


def main(argv: list[str] | None = None):
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    parser = argparse.ArgumentParser("brium")
    sub = parser.add_subparsers(dest="command", required=True)

    crawl_p = sub.add_parser("crawl")
    crawl_p.add_argument("seeds", nargs="+", help="URLs to start from")
    crawl_p.add_argument("--max-pages", type=int, default=100)
    crawl_p.add_argument("--max-depth", type=int, default=3)
    crawl_p.add_argument("--data-dir", default="crawl_data")

    search_p = sub.add_parser("search")
    search_p.add_argument("query", help="search query")
    search_p.add_argument("--top-k", type=int, default=20)
    search_p.add_argument("--data-dir", default="crawl_data")
    search_p.add_argument("--ranker", default="bm25",
                          help=f"ranking plugin ({', '.join(Registry.list_rankers())})")

    serve_p = sub.add_parser("serve")
    serve_p.add_argument("--host", default="0.0.0.0")
    serve_p.add_argument("--port", type=int, default=8000)
    serve_p.add_argument("--data-dir", default="crawl_data")
    serve_p.add_argument("--ui", action="store_true", default=False,
                         help="Use Brium UI layer instead of raw API")
    serve_p.add_argument("--ranker", default="bm25",
                         help=f"ranking plugin ({', '.join(Registry.list_rankers())})")
    serve_p.add_argument("--no-scheduler", action="store_true",
                         help="Disable background scheduler")
    serve_p.add_argument("--with-queue", action="store_true",
                         help="Enable persistent task queue for crawl jobs")

    plugins_p = sub.add_parser("plugins")
    plugins_p.add_argument("action", choices=["list"], help="list registered plugins")

    metrics_p = sub.add_parser("metrics")
    metrics_p.add_argument("--data-dir", default="crawl_data")

    args = parser.parse_args(argv)
    cfg = Config(
        data_dir=args.data_dir,
        max_depth=getattr(args, "max_depth", 5),
    )

    if args.command == "crawl":
        indexer = Indexer(cfg.index_db)
        crawler = Crawler(cfg, on_page=lambda p: indexer.add_page(p))
        crawler.seed(args.seeds)
        count = crawler.crawl(args.max_pages)
        crawler.close()
        indexer.close()
        print(f"Indexed {count} pages")

    elif args.command == "search":
        engine = SearchEngine(cfg.index_db, ranker_name=args.ranker)
        results = engine.search(args.query, args.top_k)
        print(f"{len(results)} results for '{args.query}':")
        for r in results:
            print(f"  {r.score:.4f}  {r.title}  {r.url}")
        engine.close()

    elif args.command == "serve":
        if args.ui:
            from Brium.server import build_ui
            app = build_ui(cfg, with_scheduler=not args.no_scheduler,
                           with_queue=args.with_queue, ranker_name=args.ranker)
        else:
            from brium.api.server import create_app, init_app
            app = create_app()
            init_app(app, cfg, with_scheduler=not args.no_scheduler,
                     with_queue=args.with_queue, ranker_name=args.ranker)

            @app.route("/")
            def index():
                from flask import send_from_directory
                d = os.path.join(os.path.dirname(__file__), "api", "static")
                return send_from_directory(d, "index.html")

        app.run(host=args.host, port=args.port, debug=False)

    elif args.command == "plugins":
        if args.action == "list":
            print("Rankers:", ", ".join(Registry.list_rankers()))
            print("Sources:", ", ".join(Registry.list_sources()))

    elif args.command == "metrics":
        from brium.metrics.engine import Metrics
        m = Metrics(os.path.join(args.data_dir, "metrics.db"))
        snap = m.snapshot()
        print("=== Metrics ===")
        for k, v in snap.get("counters", {}).items():
            print(f"  {k}: {v}")
        for k, v in snap.get("gauges", {}).items():
            print(f"  {k}: {v:.2f}")
        for k, v in snap.get("latency", {}).items():
            print(f"  avg_{k}: {v:.4f}s")
        cache = snap.get("cache", {})
        print(f"  cache_hits: {cache.get('hits', 0)}")
        print(f"  cache_misses: {cache.get('misses', 0)}")
        print(f"  cache_hit_ratio: {cache.get('hit_ratio', 0):.3f}")
        m.close()


if __name__ == "__main__":
    main()
