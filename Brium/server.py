from __future__ import annotations

import os

from flask import Flask, send_from_directory

from brium.base.config import Config
from brium.api.server import create_app, init_app

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(HERE, "static")


def build_ui(config: Config | None = None, with_scheduler: bool = True,
             with_queue: bool = False, ranker_name: str = "bm25") -> Flask:
    if config is None:
        config = Config()
    app = create_app()
    init_app(app, config, with_scheduler=with_scheduler,
             with_queue=with_queue, ranker_name=ranker_name)

    frontend_dir = STATIC_DIR

    @app.route("/")
    def index():
        return send_from_directory(frontend_dir, "index.html")

    @app.route("/static/<path:filename>")
    def static_files(filename: str):
        return send_from_directory(frontend_dir, filename)

    @app.route("/assets/<path:filename>")
    def asset_files(filename: str):
        assets_dir = os.path.join(HERE, "assets")
        return send_from_directory(assets_dir, filename)

    return app


def main():
    import argparse
    parser = argparse.ArgumentParser("Brium.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--data-dir", default="crawl_data")
    parser.add_argument("--ranker", default="bm25")
    parser.add_argument("--no-scheduler", action="store_true")
    parser.add_argument("--with-queue", action="store_true")
    args = parser.parse_args()
    cfg = Config(data_dir=args.data_dir)
    app = build_ui(cfg, with_scheduler=not args.no_scheduler,
                   with_queue=args.with_queue, ranker_name=args.ranker)
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
