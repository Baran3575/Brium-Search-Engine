from __future__ import annotations


class BriumError(Exception):
    pass


class CrawlError(BriumError):
    pass


class IndexError(BriumError):
    pass


class FetchError(BriumError):
    pass


class DiscoveryError(BriumError):
    pass
