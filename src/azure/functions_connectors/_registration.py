"""Registration of the Azure Functions timer trigger for connector polling."""

from __future__ import annotations

import atexit
import logging

logger = logging.getLogger(__name__)

_registration_done = False


def register_connector_triggers(
    app, poll_interval: str = "0 */1 * * * *"
) -> None:
    """Validation-only compatibility API for trigger registration.

    Shared timer + queue functions are registered by the first
    ``@generic_connection_trigger`` decorator call.
    """
    global _registration_done
    _registration_done = True


def _check_registration() -> None:
    from ._decorator import _registered_triggers

    if _registered_triggers and not _registration_done:
        logging.getLogger(__name__).warning(
            "azure-functions-connectors: @generic_connection_trigger decorators "
            "found but register_connector_triggers(app) was never called. "
            "Please call register_connector_triggers(app) after your decorators."
        )


atexit.register(_check_registration)
