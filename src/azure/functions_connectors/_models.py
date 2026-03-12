"""Data models for connector triggers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Callable

try:
    from importlib.metadata import version

    PACKAGE_VERSION = version("azure-functions-connectors")
except Exception:
    PACKAGE_VERSION = "0.0.0-dev"


# ---------------------------------------------------------------------------
# TriggerConfig
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TriggerConfig:
    """Immutable configuration captured from the decorator."""

    connection_id: str
    trigger_path: str
    trigger_queries: dict[str, str] = field(default_factory=dict)
    min_interval: int = 60
    max_interval: int = 300
    poll_function: Callable[[str, str | None], "PollResult"] | None = None


# ---------------------------------------------------------------------------
# Helper hash functions (module-level for easy import)
# ---------------------------------------------------------------------------

def compute_structural_hash(config: TriggerConfig) -> str:
    """SHA-256 of connection_id + trigger_path + trigger_queries.

    Runtime callables (e.g. poll_function) are intentionally excluded.
    """
    payload = json.dumps(
        {
            "connection_id": config.connection_id,
            "trigger_path": config.trigger_path,
            "trigger_queries": config.trigger_queries,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def compute_runtime_hash(config: TriggerConfig) -> str:
    """SHA-256 of package_version + min_interval + max_interval."""
    payload = json.dumps(
        {
            "package_version": PACKAGE_VERSION,
            "min_interval": config.min_interval,
            "max_interval": config.max_interval,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def compute_instance_id(config: TriggerConfig) -> str:
    """Return ``ctp:<first-12-chars-of-structural-hash>``."""
    return f"ctp:{compute_structural_hash(config)[:12]}"


# ---------------------------------------------------------------------------
# TriggerRegistration
# ---------------------------------------------------------------------------

@dataclass
class TriggerRegistration:
    """A registered trigger (config + handler + computed IDs)."""

    config: TriggerConfig
    handler: Callable
    instance_id: str = field(init=False)
    structural_hash: str = field(init=False)
    runtime_hash: str = field(init=False)

    def __post_init__(self) -> None:
        self.structural_hash = compute_structural_hash(self.config)
        self.runtime_hash = compute_runtime_hash(self.config)
        self.instance_id = compute_instance_id(self.config)


# ---------------------------------------------------------------------------
# TriggerState
# ---------------------------------------------------------------------------

@dataclass
class TriggerState:
    """Persisted blob state for a trigger instance."""

    cursor: str | None = None
    last_poll_utc: str | None = None
    backoff_seconds: int = 60
    consecutive_empty: int = 0
    structural_hash: str | None = None
    runtime_hash: str | None = None

    def to_dict(self) -> dict:
        return {
            "cursor": self.cursor,
            "last_poll_utc": self.last_poll_utc,
            "backoff_seconds": self.backoff_seconds,
            "consecutive_empty": self.consecutive_empty,
            "structural_hash": self.structural_hash,
            "runtime_hash": self.runtime_hash,
        }

    @classmethod
    def from_dict(cls, d: dict) -> TriggerState:
        return cls(
            cursor=d.get("cursor"),
            last_poll_utc=d.get("last_poll_utc"),
            backoff_seconds=d.get("backoff_seconds", 60),
            consecutive_empty=d.get("consecutive_empty", 0),
            structural_hash=d.get("structural_hash"),
            runtime_hash=d.get("runtime_hash"),
        )


# ---------------------------------------------------------------------------
# PollResult
# ---------------------------------------------------------------------------

@dataclass
class PollResult:
    """Result returned from a single poll request."""

    status: int
    items: list[dict] = field(default_factory=list)
    cursor: str | None = None
    retry_after: int | None = None


class ConnectorItem:
    """Base class for typed connector items.

    Exposes snake_case properties for common fields while also supporting
    direct dict-style access (``item["Key"]``, ``item.get("Key")``).
    """

    def __init__(self, data: dict) -> None:
        self._data = data

    # -- dict-like access -----------------------------------------------------

    def __getitem__(self, key: str):
        return self._data[key]

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    def to_dict(self) -> dict:
        """Return the underlying raw dict."""
        return self._data

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._data})"
