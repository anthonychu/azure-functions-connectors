"""Registration of Azure Functions timer + queue triggers for connector polling."""

from __future__ import annotations

import atexit
import logging

import azure.functions as func

from ._cleanup import cleanup_orphan_states
from ._poller import poll_all_triggers
from ._processor import process_queue_message

logger = logging.getLogger(__name__)

_registration_done = False
_cleanup_done = False


def register_connector_triggers(
    app, poll_interval: str = "0 */1 * * * *"
) -> None:
    """Register the poller (timer) and processor (queue) functions on *app*."""
    global _registration_done
    _registration_done = True

    # -- Timer: polls connectors, enqueues items ----
    @app.function_name("ConnectorTriggerPoller")
    @app.timer_trigger(
        schedule=poll_interval,
        arg_name="timer",
        run_on_startup=True,
    )
    async def connector_trigger_poller(timer: func.TimerRequest) -> None:
        global _cleanup_done
        if not _cleanup_done:
            await cleanup_orphan_states()
            _cleanup_done = True
        await poll_all_triggers()

    # -- Queue: processes individual items ----
    @app.function_name("ConnectorTriggerProcessor")
    @app.queue_trigger(
        arg_name="msg",
        queue_name="connector-trigger-items",
        connection="AzureWebJobsStorage",
    )
    async def connector_trigger_processor(msg: func.QueueMessage) -> None:  # noqa: ARG001
        await process_queue_message(msg.get_body().decode("utf-8"))


def _check_registration() -> None:
    from ._decorator import _registered_triggers

    if _registered_triggers and not _registration_done:
        logging.getLogger(__name__).error(
            "azure-functions-connectors: @generic_connection_trigger decorators "
            "found but register_connector_triggers(app) was never called. "
            "Triggers will NOT fire."
        )


atexit.register(_check_registration)
