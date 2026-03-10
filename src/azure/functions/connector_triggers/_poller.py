"""Timer-based poller for connector triggers."""

from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os

from azure.storage.queue.aio import QueueClient

from ._decorator import get_registered_triggers
from ._dynamic_invoke import poll_trigger
from ._env import resolve_config
from ._models import PollResult, TriggerRegistration, TriggerState
from ._state import (
    acquire_trigger_lease,
    read_state,
    release_trigger_lease,
    save_state,
)

logger = logging.getLogger(__name__)

_QUEUE_NAME = "connector-trigger-items"
_MAX_CONCURRENCY = 5


async def poll_all_triggers() -> None:
    """Poll every registered trigger concurrently (max 5 at a time)."""
    triggers = get_registered_triggers()
    if not triggers:
        return

    semaphore = asyncio.Semaphore(_MAX_CONCURRENCY)

    async def _bounded(trigger: TriggerRegistration) -> None:
        async with semaphore:
            await _poll_single_trigger(trigger)

    await asyncio.gather(*[_bounded(t) for t in triggers])


async def _poll_single_trigger(trigger: TriggerRegistration) -> None:
    """Poll a single trigger: lease -> read state -> poll -> enqueue -> save."""
    instance_id = trigger.instance_id
    lease_id: str | None = None

    try:
        # -- acquire lease ---------------------------------------------------
        lease_id = await acquire_trigger_lease(instance_id)
        if lease_id is None:
            logger.debug("Skipping %s -- lease held by another instance", instance_id)
            return

        # -- read state ------------------------------------------------------
        state = await read_state(instance_id)

        # -- config change detection -----------------------------------------
        if state is not None:
            if state.structural_hash != trigger.structural_hash:
                # Data source changed -- full reset
                state = None
            elif state.runtime_hash != trigger.runtime_hash:
                # Runtime params changed -- keep cursor, update hash
                state.runtime_hash = trigger.runtime_hash

        # -- backoff check ---------------------------------------------------
        now = datetime.datetime.now(datetime.timezone.utc)
        if state is not None and state.last_poll_utc is not None:
            last_poll = datetime.datetime.fromisoformat(state.last_poll_utc)
            elapsed = (now - last_poll).total_seconds()
            if elapsed < state.backoff_seconds:
                logger.debug(
                    "Skipping %s -- backoff (%ds remaining)",
                    instance_id,
                    int(state.backoff_seconds - elapsed),
                )
                return

        # -- resolve env vars ------------------------------------------------
        connection_id, trigger_path, trigger_queries = resolve_config(
            trigger.config.connection_id,
            trigger.config.trigger_path,
            trigger.config.trigger_queries,
        )

        # -- poll (sync call -> run in thread) -------------------------------
        cursor = state.cursor if state else None
        result: PollResult = await asyncio.to_thread(
            poll_trigger, connection_id, trigger_path, trigger_queries, cursor
        )

        # -- build new state -------------------------------------------------
        new_state = state if state is not None else TriggerState()
        new_state.cursor = result.cursor if result.cursor is not None else new_state.cursor
        new_state.last_poll_utc = now.isoformat()
        new_state.structural_hash = trigger.structural_hash
        new_state.runtime_hash = trigger.runtime_hash

        if result.status == 200 and result.items:
            # Items found -- enqueue and reset backoff
            await _enqueue_items(instance_id, result.items)
            new_state.backoff_seconds = trigger.config.min_interval
            new_state.consecutive_empty = 0
            logger.info(
                "Polled %s -- %d item(s) enqueued", instance_id, len(result.items)
            )
        else:
            # Empty poll (202 / no items) -- exponential backoff
            new_state.consecutive_empty += 1
            if result.retry_after is not None:
                new_state.backoff_seconds = result.retry_after
            else:
                new_state.backoff_seconds = min(
                    new_state.backoff_seconds * 2,
                    trigger.config.max_interval,
                )
            logger.debug(
                "Polled %s -- empty (status=%d, next backoff=%ds)",
                instance_id,
                result.status,
                new_state.backoff_seconds,
            )

        # -- save state ------------------------------------------------------
        await save_state(instance_id, new_state)

    except Exception:
        logger.warning("Error polling trigger %s", instance_id, exc_info=True)
    finally:
        if lease_id is not None:
            try:
                await release_trigger_lease(instance_id, lease_id)
            except Exception:
                logger.warning(
                    "Failed to release lease for %s", instance_id, exc_info=True
                )


async def _enqueue_items(instance_id: str, items: list[dict]) -> None:
    """Send each item as a JSON message to the Storage Queue."""
    conn_str = os.environ.get("AzureWebJobsStorage")
    if not conn_str:
        raise ValueError("AzureWebJobsStorage environment variable is not set")

    queue_client = QueueClient.from_connection_string(conn_str, _QUEUE_NAME)
    try:
        try:
            await queue_client.create_queue()
        except Exception:
            pass  # queue already exists

        for item in items:
            message = json.dumps({"instance_id": instance_id, "item": item})
            await queue_client.send_message(message)
    finally:
        await queue_client.close()
