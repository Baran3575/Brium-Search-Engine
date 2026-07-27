from __future__ import annotations

from dataclasses import dataclass, field

CURRENT_API_VERSION = "1.0"
SUPPORTED_API_VERSIONS = {"1.0"}


@dataclass
class PluginMetadata:
    name: str = "unknown"
    version: str = "0.1.0"
    api_version: str = CURRENT_API_VERSION
    description: str = ""
    author: str = ""
    dependencies: list[str] = field(default_factory=list)
