"""Queue message processor — thin dispatch layer for connector triggers."""

from __future__ import annotations

import asyncio
import json
import logging

from ._decorator import get_handler
from ._poller import retrieve_item_blob

logger = logging.getLogger(__name__)


async def process_queue_message(msg_body: str) -> None:
    """Parse a queue message and dispatch to the registered handler."""
    try:
        payload = json.loads(msg_body)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error("Malformed queue message, dropping: %s", e)
        return

    instance_id = payload.get("instance_id")
    if not instance_id:
        logger.error("Queue message missing instance_id, dropping")
        return

    try:
        if "item_blob" in payload:
            item = await retrieve_item_blob(payload["item_blob"])
        else:
            item = payload.get("item")
            if item is None:
                logger.error("Queue message missing item/item_blob for %s, dropping", instance_id)
                return
    except Exception as e:
        logger.error("Failed to retrieve item for %s: %s", instance_id, e)
        raise  # Let queue retry

    handler = get_handler(instance_id)
    if handler is None:
        logger.warning("No handler registered for %s, dropping item", instance_id)
        return

    if asyncio.iscoroutinefunction(handler):
        await handler(item)
    else:
        handler(item)

    logger.debug("Processed item for %s", instance_id)
