"""Decorator for registering connector trigger handlers."""

from __future__ import annotations

from typing import Callable

from ._models import TriggerConfig, TriggerRegistration

_registered_triggers: list[TriggerRegistration] = []
_handler_registry: dict[str, Callable] = {}  # instance_id → handler


def generic_connection_trigger(
    connection_id: str,
    trigger_path: str,
    trigger_queries: dict[str, str] | None = None,
    min_interval: int = 60,
    max_interval: int = 300,
) -> Callable:
    """Register a function as a connector-trigger handler.

    Stores RAW (unresolved) values; env-var resolution happens at startup.
    """

    def decorator(func: Callable) -> Callable:
        config = TriggerConfig(
            connection_id=connection_id,
            trigger_path=trigger_path,
            trigger_queries=trigger_queries or {},
            min_interval=min_interval,
            max_interval=max_interval,
        )
        registration = TriggerRegistration(config=config, handler=func)
        _registered_triggers.append(registration)
        _handler_registry[registration.instance_id] = func
        return func

    return decorator


def get_registered_triggers() -> list[TriggerRegistration]:
    """Return all registered trigger registrations."""
    return _registered_triggers


def get_handler(instance_id: str) -> Callable | None:
    """Return the handler for the given instance_id, or None."""
    return _handler_registry.get(instance_id)
