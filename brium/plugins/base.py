from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class RankerResult:
    url: str
    title: str
    score: float
    snippet: str = ""


class BaseRanker(ABC):
    name: str = "base"

    @abstractmethod
    def rank(self, raw_query: str, conn, top_k: int = 20) -> list[RankerResult]:
        ...


class BaseSource(ABC):
    name: str = "base"

    @abstractmethod
    def discover(self, query: str) -> list[str]:
        ...
