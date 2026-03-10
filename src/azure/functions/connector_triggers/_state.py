"""Blob-backed state management for connector trigger instances."""

from __future__ import annotations

import json
import os

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.storage.blob.aio import BlobServiceClient

from ._models import TriggerState

_CONTAINER_NAME = "connector-trigger-state"
_BLOB_PREFIX = "triggers/"

_blob_service_client: BlobServiceClient | None = None
_container_ensured = False


def _get_blob_service_client() -> BlobServiceClient:
    global _blob_service_client
    if _blob_service_client is None:
        conn_str = os.environ.get("AzureWebJobsStorage")
        if not conn_str:
            raise ValueError(
                "AzureWebJobsStorage environment variable is not set"
            )
        _blob_service_client = BlobServiceClient.from_connection_string(conn_str)
    return _blob_service_client


async def _ensure_container() -> None:
    global _container_ensured
    if _container_ensured:
        return
    client = _get_blob_service_client()
    container = client.get_container_client(_CONTAINER_NAME)
    try:
        await container.create_container()
    except ResourceExistsError:
        pass
    _container_ensured = True


def _blob_path(instance_id: str) -> str:
    return f"{_BLOB_PREFIX}{instance_id}.json"


async def read_state(instance_id: str) -> TriggerState | None:
    """Read trigger state from blob storage, or *None* if it doesn't exist."""
    await _ensure_container()
    client = _get_blob_service_client()
    blob = client.get_blob_client(_CONTAINER_NAME, _blob_path(instance_id))
    try:
        download = await blob.download_blob()
        raw = await download.readall()
        data = json.loads(raw)
        return TriggerState.from_dict(data)
    except ResourceNotFoundError:
        return None


async def save_state(instance_id: str, state: TriggerState) -> None:
    """Persist trigger state as JSON to blob storage."""
    await _ensure_container()
    client = _get_blob_service_client()
    blob = client.get_blob_client(_CONTAINER_NAME, _blob_path(instance_id))
    payload = json.dumps(state.to_dict())
    await blob.upload_blob(payload, overwrite=True)


async def delete_state(instance_id: str) -> None:
    """Delete the state blob for a trigger instance; ignore if not found."""
    client = _get_blob_service_client()
    blob = client.get_blob_client(_CONTAINER_NAME, _blob_path(instance_id))
    try:
        await blob.delete_blob()
    except ResourceNotFoundError:
        pass


async def list_state_ids() -> list[str]:
    """Return all persisted instance IDs (without prefix/suffix)."""
    await _ensure_container()
    client = _get_blob_service_client()
    container = client.get_container_client(_CONTAINER_NAME)
    ids: list[str] = []
    async for blob in container.list_blobs(name_starts_with=_BLOB_PREFIX):
        name: str = blob.name
        if name.endswith(".json"):
            instance_id = name[len(_BLOB_PREFIX) : -len(".json")]
            ids.append(instance_id)
    return ids


async def acquire_trigger_lease(
    instance_id: str, lease_duration: int = 60
) -> str | None:
    """Try to acquire a lease on the trigger's state blob.

    Returns the lease ID on success, or *None* if the blob is already leased.
    If the blob does not exist it is created first.
    """
    await _ensure_container()
    client = _get_blob_service_client()
    blob = client.get_blob_client(_CONTAINER_NAME, _blob_path(instance_id))

    try:
        lease = await blob.acquire_lease(lease_duration=lease_duration)
        return lease.id
    except ResourceNotFoundError:
        # Blob doesn't exist yet — seed it, then lease.
        await blob.upload_blob(b"{}", overwrite=True)
        lease = await blob.acquire_lease(lease_duration=lease_duration)
        return lease.id
    except Exception:  # HttpResponseError when already leased (409)
        return None


async def release_trigger_lease(instance_id: str, lease_id: str) -> None:
    """Release a previously acquired lease."""
    client = _get_blob_service_client()
    blob = client.get_blob_client(_CONTAINER_NAME, _blob_path(instance_id))
    lease = blob.get_blob_lease_client(lease_id)  # type: ignore[arg-type]
    await lease.release()
