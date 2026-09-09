"""An operation-local source snapshot. Instances are never cached across requests."""

from dataclasses import dataclass
from typing import Any


class ConfiguratorDataError(ValueError):
    pass


@dataclass(frozen=True)
class SourceSnapshot:
    index: dict[str, Any]
    catalogs: dict[str, dict[str, dict[str, Any]]]
    guides: dict[str, dict[str, Any]]
