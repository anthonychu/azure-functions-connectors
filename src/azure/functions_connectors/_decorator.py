"""Decorator for registering connector trigger handlers."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Callable

import azure.functions as func

from ._models import ConnectorItem, TriggerConfig, TriggerRegistration

logger = logging.getLogger(__name__)


def _queue_name_for(func_name: str) -> str:
    """Derive a queue name from the user's function name."""
    return f"ct-{func_name.replace('_', '-').lower()}"[:63]


class FunctionsConnectors:
    """Builder that registers connector trigger handlers on an Azure Functions app.

    Usage::

        connectors = FunctionsConnectors(app)

        @connectors.generic_trigger(
            connection_id="%OFFICE365_CONNECTION_ID%",
            trigger_path="/Mail/OnNewEmail",
        )
        async def on_new_email(item: dict):
            ...
    """

    def __init__(self, app: func.FunctionApp) -> None:
        self._app = app
        self._registered_triggers: list[TriggerRegistration] = []
        self._queue_handlers: dict[str, list[tuple[Callable, str]]] = {}
        self._timer_registered = False

        # Typed trigger builders
        from ._triggers.office365 import Office365Triggers
        from ._triggers.salesforce import SalesforceTriggers
        from ._triggers.sharepoint import SharePointTriggers
        from ._triggers.teams import TeamsTriggers
        self.office365 = Office365Triggers(self)
        self.salesforce = SalesforceTriggers(self)
        self.sharepoint = SharePointTriggers(self)
        self.teams = TeamsTriggers(self)

        # Set module-level ref so poller/cleanup can access us
        global _active_connectors
        _active_connectors = self

    def get_client(self, connection_id: str):
        """Get a generic connector client for calling any action."""
        from ._client import ConnectorClient
        return ConnectorClient(connection_id)

    def generic_trigger(
        self,
        connection_id: str,
        trigger_path: str,
        trigger_queries: dict[str, str] | None = None,
        min_interval: int = 60,
        max_interval: int = 300,
        poll_function: Callable | None = None,
    ) -> Callable:
        """Register a function as a connector-trigger handler."""

        if min_interval < 1:
            raise ValueError("min_interval must be >= 1")
        if max_interval < min_interval:
            raise ValueError(
                f"max_interval ({max_interval}) must be >= min_interval ({min_interval})"
            )

        def decorator(user_func: Callable) -> Callable:
            config = TriggerConfig(
                connection_id=connection_id,
                trigger_path=trigger_path,
                trigger_queries=trigger_queries or {},
                min_interval=min_interval,
                max_interval=max_interval,
                poll_function=poll_function,
            )
            registration = TriggerRegistration(config=config, handler=user_func)
            self._registered_triggers.append(registration)

            queue_name = _queue_name_for(user_func.__name__)
            self._queue_handlers.setdefault(queue_name, []).append(
                (user_func, registration.instance_id)
            )

            if not self._timer_registered:
                self._timer_registered = True
                self._register_timer()

            self._register_queue_function(user_func, queue_name)

            print(
                f"[azure.functions_connectors] Registered trigger: "
                f"{config.trigger_path} → {user_func.__name__} (queue: {queue_name})"
            )

            return user_func

        return decorator

    def _register_timer(self) -> None:
        from ._cleanup import cleanup_orphan_states
        from ._poller import poll_all_triggers

        cleanup_done = False

        @self._app.generic_trigger(
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

    def _register_queue_function(self, user_func: Callable, queue_name: str) -> None:
        from ._poller import retrieve_item_blob

        func_name = user_func.__name__

        # Detect typed item model from handler's type hint.
        # Use get_type_hints() to resolve string annotations from
        # `from __future__ import annotations`.
        item_type = None
        try:
            import typing
            hints = typing.get_type_hints(user_func)
            for param_name, param_type in hints.items():
                if param_type is not dict and isinstance(param_type, type) and issubclass(param_type, ConnectorItem):
                    item_type = param_type
                break
        except Exception as e:
            logger.debug("Could not resolve type hints for %s: %s", func_name, e)

        async def queue_processor(msg: func.QueueMessage) -> None:
            body = msg.get_body().decode("utf-8")
            try:
                payload = json.loads(body)
            except (json.JSONDecodeError, TypeError):
                logger.error("[%s] Malformed queue message, dropping", func_name)
                return

            item = payload.get("item")
            if item is None:
                item_blob = payload.get("item_blob")
                if item_blob:
                    item = await retrieve_item_blob(item_blob)
                else:
                    logger.error("[%s] Missing item, dropping", func_name)
                    return

            # Auto-wrap in typed model if handler expects one
            if item_type is not None and isinstance(item, dict):
                item = item_type(item)

            if asyncio.iscoroutinefunction(user_func):
                await user_func(item)
            else:
                user_func(item)

        queue_processor.__name__ = func_name

        self._app.generic_trigger(
            arg_name="msg",
            type="queueTrigger",
            queueName=queue_name,
            connection="AzureWebJobsStorage",
        )(queue_processor)

    def get_registered_triggers(self) -> list[TriggerRegistration]:
        return self._registered_triggers

    def get_queue_names_for_instance(self, instance_id: str) -> list[str]:
        queues = []
        for queue_name, handlers in self._queue_handlers.items():
            for _, iid in handlers:
                if iid == instance_id:
                    queues.append(queue_name)
        return queues


# Module-level reference, set by FunctionsConnectors.__init__
_active_connectors: FunctionsConnectors | None = None
