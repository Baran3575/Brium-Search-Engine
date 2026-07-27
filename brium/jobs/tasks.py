from __future__ import annotations

import logging
import time

from brium.cache.engine import Cache
from brium.base.config import Config
from brium.base.constants import NEWS_RSS, DEFAULT_HOMEPAGES
from brium.discovery.rss import parse_rss
from brium.crawl.spider import Crawler
from brium.index.engine import Indexer

log = logging.getLogger(__name__)


def refresh_rss(cache: Cache | None = None) -> int:
    count = 0
    for url in NEWS_RSS:
        links = parse_rss(url)
        count += len(links)
        if cache:
            cache.set("rss", url, "\n".join(links), ttl_seconds=600)
    log.info("refreshed %d RSS feeds, %d links total", len(NEWS_RSS), count)
    return count


def cleanup_cache(cache: Cache) -> int:
    deleted = cache.clear_expired()
    if deleted:
        log.info("cleared %d expired cache entries", deleted)
    return deleted


def crawl_homepages(config: Config, indexer: Indexer | None = None) -> int:
    if not DEFAULT_HOMEPAGES:
        return 0
    if indexer is None:
        indexer = Indexer(config.index_db)
        should_close = True
    else:
        should_close = False

    try:
        total = 0
        for url in DEFAULT_HOMEPAGES[:3]:
            crawler = Crawler(config, on_page=lambda p: indexer.add_page(p))
            crawler.seed([url])
            count = crawler.crawl(5)
            crawler.close()
            total += count
            time.sleep(1)
        log.info("crawled %d pages from homepages", total)
        return total
    finally:
        if should_close:
            indexer.close()


def optimize_index(indexer: Indexer) -> str | None:
    try:
        indexer.conn.execute("PRAGMA optimize")
        indexer.conn.commit()
        log.info("index optimization complete")
        return "ok"
    except Exception as e:
        log.warning("index optimization failed: %s", e)
        return None


def get_rss_refresh_job(cache: Cache | None = None):
    from brium.jobs.scheduler import Job
    def _run():
        refresh_rss(cache)
    return Job("rss-refresh", 600.0, _run)


def get_cache_cleanup_job(cache: Cache):
    from brium.jobs.scheduler import Job
    def _run():
        cleanup_cache(cache)
    return Job("cache-cleanup", 1800.0, _run)


def get_index_optimize_job(indexer: Indexer):
    from brium.jobs.scheduler import Job
    def _run():
        optimize_index(indexer)
    return Job("index-optimize", 3600.0, _run)
