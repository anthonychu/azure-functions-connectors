"""Timer-based poller for connector triggers."""

from __future__ import annotations

import asyncio
import base64
import datetime
import json
import logging
import os
import uuid

from azure.storage.blob.aio import BlobServiceClient
from azure.storage.queue.aio import QueueClient

from ._decorator import _active_connectors
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

_MAX_CONCURRENCY = 5
_CONTAINER_NAME = "connector-trigger-state"
_ITEMS_BLOB_PREFIX = "items/"
MAX_QUEUE_MESSAGE_BYTES = 48 * 1024  # 48KB, leaving margin for base64 encoding overhead


async def poll_all_triggers() -> None:
    """Poll every unique trigger concurrently (max 5 at a time).

    Multiple handlers on the same trigger path share one poll — dedup by instance_id.
    """
    triggers = _active_connectors.get_registered_triggers() if _active_connectors else []
    if not triggers:
        return

    # Deduplicate: only poll each unique instance_id once
    seen: set[str] = set()
    unique_triggers: list[TriggerRegistration] = []
    for t in triggers:
        if t.instance_id not in seen:
            seen.add(t.instance_id)
            unique_triggers.append(t)

    semaphore = asyncio.Semaphore(_MAX_CONCURRENCY)

    async def _bounded(trigger: TriggerRegistration) -> None:
        async with semaphore:
            await _poll_single_trigger(trigger)

    await asyncio.gather(*[_bounded(t) for t in unique_triggers])


async def _poll_single_trigger(trigger: TriggerRegistration) -> None:
    """Poll a single trigger: lease -> read state -> poll -> enqueue -> save."""
    instance_id = trigger.instance_id
    lease_id: str | None = None

    try:
        # -- acquire lease ---------------------------------------------------
        lease_id = await acquire_trigger_lease(instance_id, lease_duration=60)
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
            try:
                last_poll = datetime.datetime.fromisoformat(state.last_poll_utc)
            except (ValueError, TypeError):
                logging.warning(
                    "Corrupt last_poll_utc for %s, resetting state",
                    instance_id,
                )
                state = None

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
            # Renew lease before enqueuing many items to avoid expiry
            if len(result.items) > 10 and lease_id:
                try:
                    from ._state import _get_blob_service_client, _CONTAINER_NAME, _blob_path
                    from azure.storage.blob.aio import BlobLeaseClient
                    blob_client = _get_blob_service_client().get_blob_client(
                        _CONTAINER_NAME, _blob_path(instance_id)
                    )
                    lease_obj = BlobLeaseClient(blob_client, lease_id=lease_id)
                    await lease_obj.renew()
                except Exception:
                    pass  # Best effort renewal

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
        await save_state(instance_id, new_state, lease_id=lease_id)

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


async def _store_item_blob(blob_path: str, item: dict) -> None:
    """Store an oversized item in blob storage."""
    conn_str = os.environ.get("AzureWebJobsStorage")
    if not conn_str:
        raise ValueError("AzureWebJobsStorage environment variable is not set")

    blob_service = BlobServiceClient.from_connection_string(conn_str)
    try:
        blob_client = blob_service.get_blob_client(_CONTAINER_NAME, blob_path)
        await blob_client.upload_blob(json.dumps(item), overwrite=True)
    finally:
        await blob_service.close()


async def retrieve_item_blob(blob_path: str) -> dict:
    """Retrieve an oversized item from blob storage.

    The blob is NOT deleted here — it will be cleaned up after the handler
    succeeds. If the handler fails and the queue message retries, the blob
    must still be available.
    """
    conn_str = os.environ.get("AzureWebJobsStorage")
    if not conn_str:
        raise ValueError("AzureWebJobsStorage environment variable is not set")

    blob_service = BlobServiceClient.from_connection_string(conn_str)
    try:
        blob_client = blob_service.get_blob_client(_CONTAINER_NAME, blob_path)
        download = await blob_client.download_blob()
        raw = await download.readall()
        return json.loads(raw)
    finally:
        await blob_service.close()


async def _enqueue_items(instance_id: str, items: list[dict]) -> None:
    """Send each item to all per-handler queues for this instance_id.

    Items larger than *MAX_QUEUE_MESSAGE_BYTES* are stored in blob storage and
    a lightweight pointer message is enqueued instead.
    """
    from ._decorator import _active_connectors

    if not _active_connectors:
        logger.warning("No active connectors, skipping enqueue")
        return

    queue_names = _active_connectors.get_queue_names_for_instance(instance_id)
    if not queue_names:
        logger.warning("No queues registered for %s, skipping enqueue", instance_id)
        return

    conn_str = os.environ.get("AzureWebJobsStorage")
    if not conn_str:
        raise ValueError("AzureWebJobsStorage environment variable is not set")

    for queue_name in queue_names:
        queue_client = QueueClient.from_connection_string(conn_str, queue_name)
        try:
            try:
                await queue_client.create_queue()
            except Exception:
                pass  # queue already exists

            for item in items:
                message = json.dumps({"item": item})
                if len(message.encode("utf-8")) > MAX_QUEUE_MESSAGE_BYTES:
                    blob_path = f"{_ITEMS_BLOB_PREFIX}{instance_id}/{uuid.uuid4()}.json"
                    await _store_item_blob(blob_path, item)
                    message = json.dumps({"item_blob": blob_path})
                # Base64-encode: the Functions host (.NET) expects base64 queue messages
                encoded = base64.b64encode(message.encode("utf-8")).decode("utf-8")
                await queue_client.send_message(encoded)
        finally:
            await queue_client.close()
