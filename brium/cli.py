from __future__ import annotations

import argparse
import logging

from brium.config import Config
from brium.crawler.spider import Crawler, Page
from brium.indexer.indexer import Indexer
from brium.search.engine import SearchEngine


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

    serve_p = sub.add_parser("serve")
    serve_p.add_argument("--host", default="0.0.0.0")
    serve_p.add_argument("--port", type=int, default=8000)
    serve_p.add_argument("--data-dir", default="crawl_data")

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
        engine = SearchEngine(cfg.index_db)
        results = engine.search(args.query, args.top_k)
        print(f"{len(results)} results for '{args.query}':")
        for r in results:
            print(f"  {r.score:.4f}  {r.title}  {r.url}")
        engine.close()

    elif args.command == "serve":
        from brium.api.server import init as api_init, app
        api_init(cfg)
        app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
