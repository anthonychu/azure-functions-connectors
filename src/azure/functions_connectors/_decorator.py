"""Decorator for registering connector trigger handlers."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Callable

import azure.functions as func

from ._models import TriggerConfig, TriggerRegistration

logger = logging.getLogger(__name__)

_registered_triggers: list[TriggerRegistration] = []
_handler_registry: dict[str, list[Callable]] = {}  # instance_id → [handlers]
_functions_registered = False  # True once timer+queue functions are registered


def generic_connection_trigger(
    app: func.FunctionApp,
    connection_id: str,
    trigger_path: str,
    trigger_queries: dict[str, str] | None = None,
    min_interval: int = 60,
    max_interval: int = 300,
) -> Callable:
    """Register a function as a connector-trigger handler.

    On the first decorator invocation, both shared poller and queue
    processor functions are registered on *app*. Subsequent invocations
    only add handlers to the in-memory registry.
    """

    if min_interval < 1:
        raise ValueError("min_interval must be >= 1")
    if max_interval < min_interval:
        raise ValueError(f"max_interval ({max_interval}) must be >= min_interval ({min_interval})")

    def decorator(user_func: Callable) -> Callable:
        global _functions_registered

        config = TriggerConfig(
            connection_id=connection_id,
            trigger_path=trigger_path,
            trigger_queries=trigger_queries or {},
            min_interval=min_interval,
            max_interval=max_interval,
        )
        registration = TriggerRegistration(config=config, handler=user_func)
        _registered_triggers.append(registration)
        _handler_registry.setdefault(registration.instance_id, []).append(user_func)

        # On FIRST decorator call only, register timer + queue on app
        if not _functions_registered:
            _functions_registered = True
            _register_functions(app)

        logger.info(
            "Registered connector trigger: %s → %s (instance: %s)",
            registration.config.trigger_path,
            user_func.__name__,
            registration.instance_id,
        )
        print(
            f"[azure.functions_connectors] Registered trigger: "
            f"{registration.config.trigger_path} → {user_func.__name__}"
        )

        return user_func

    return decorator


def _register_functions(app: func.FunctionApp) -> None:
    """Register shared poller and queue functions exactly once.

    Uses ``app.generic_trigger`` instead of typed decorators to avoid
    a Python V2 worker bug that leaks binding metadata between functions.
    """
    from ._cleanup import cleanup_orphan_states
    from ._poller import poll_all_triggers, retrieve_item_blob

    cleanup_done = False

    @app.generic_trigger(
        arg_name="timer",
        type="timerTrigger",
        schedule="0 */1 * * * *",
        runOnStartup=True,
    )
    async def ConnectorTriggerPoller(timer) -> None:
        nonlocal cleanup_done
        if not cleanup_done:
            await cleanup_orphan_states()
            cleanup_done = True
        await poll_all_triggers()

    @app.generic_trigger(
        arg_name="msg",
        type="queueTrigger",
        queueName="connector-trigger-items",
        connection="AzureWebJobsStorage",
    )
    async def ConnectorTriggerProcessor(msg: func.QueueMessage) -> None:
        body = msg.get_body().decode("utf-8")
        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, TypeError):
            logger.error("Malformed queue message, dropping")
            return

        instance_id = payload.get("instance_id")
        if not instance_id:
            logger.error("Missing instance_id, dropping")
            return

        item = payload.get("item")
        if item is None:
            item_blob = payload.get("item_blob")
            if item_blob:
                item = await retrieve_item_blob(item_blob)
            else:
                logger.error("Missing item for %s", instance_id)
                return

        handlers = _handler_registry.get(instance_id, [])
        if not handlers:
            logger.warning("No handlers for %s, dropping", instance_id)
            return

        for handler in handlers:
            if asyncio.iscoroutinefunction(handler):
                await handler(item)
            else:
                handler(item)

        logger.info("Processed item for %s (%d handler(s))", instance_id, len(handlers))


def get_registered_triggers() -> list[TriggerRegistration]:
    """Return all registered trigger registrations."""
    return _registered_triggers


def get_handlers(instance_id: str) -> list[Callable]:
    """Return all handlers for the given instance_id."""
    return _handler_registry.get(instance_id, [])
