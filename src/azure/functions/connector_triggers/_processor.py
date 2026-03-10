"""Queue message processor — thin dispatch layer for connector triggers."""

from __future__ import annotations

import asyncio
import json
import logging

from ._decorator import get_handler

logger = logging.getLogger(__name__)


async def process_queue_message(msg_body: str) -> None:
    """Parse a queue message and dispatch to the registered handler."""
    payload = json.loads(msg_body)
    instance_id: str = payload["instance_id"]
    item = payload["item"]

    handler = get_handler(instance_id)
    if handler is None:
        logger.warning("No handler registered for %s, dropping item", instance_id)
        return

    if asyncio.iscoroutinefunction(handler):
        await handler(item)
    else:
        handler(item)

    logger.debug("Processed item for %s", instance_id)
