"""ARM dynamicInvoke client for polling connector triggers."""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from urllib.parse import urlparse, parse_qs

from azure.identity import DefaultAzureCredential

from ._models import PollResult

logger = logging.getLogger(__name__)

_ARM_BASE = "https://management.azure.com"
_API_VERSION = "2016-06-01"

# Map ARM status-code strings to HTTP integers.
_STATUS_MAP: dict[str, int] = {
    "OK": 200,
    "Accepted": 202,
    "NoContent": 204,
    "BadRequest": 400,
    "Unauthorized": 401,
    "Forbidden": 403,
    "NotFound": 404,
    "InternalServerError": 500,
}


def poll_trigger(
    connection_id: str,
    trigger_path: str,
    trigger_queries: dict,
    cursor: str | None = None,
) -> PollResult:
    """Poll a connector trigger via the ARM dynamicInvoke endpoint.

    Parameters
    ----------
    connection_id:
        Full ARM resource ID, e.g.
        ``/subscriptions/.../connections/office365``.
    trigger_path:
        The trigger-specific API path forwarded inside dynamicInvoke.
    trigger_queries:
        Extra query parameters for the inner request.
    cursor:
        Opaque ``LastPollInformation`` value from a previous poll.

    Returns
    -------
    PollResult
        Parsed poll result with status, items, cursor, and retry_after.
    """
    url = f"{_ARM_BASE}{connection_id}/dynamicInvoke?api-version={_API_VERSION}"

    queries = dict(trigger_queries)
    if cursor is not None:
        queries["LastPollInformation"] = cursor

    body = json.dumps({
        "request": {
            "method": "GET",
            "path": trigger_path,
            "queries": queries,
        }
    }).encode()

    credential = DefaultAzureCredential()
    try:
        token = credential.get_token("https://management.azure.com/.default").token
    finally:
        credential.close()

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        logger.warning("dynamicInvoke HTTP error %s: %s", exc.code, exc.reason)
        return PollResult(status=exc.code, items=[])
    except urllib.error.URLError as exc:
        logger.warning("dynamicInvoke URL error: %s", exc.reason)
        return PollResult(status=500, items=[])
    except json.JSONDecodeError as exc:
        logger.warning("dynamicInvoke JSON parse error: %s", exc)
        return PollResult(status=500, items=[])

    return _parse_response(data)


def _parse_response(data: dict) -> PollResult:
    """Turn the ARM dynamicInvoke wrapper into a ``PollResult``."""
    inner = data.get("response", {})

    # --- status ----------------------------------------------------------
    status_str = inner.get("statusCode", "InternalServerError")
    status = _STATUS_MAP.get(status_str, 500)

    # --- items -----------------------------------------------------------
    body = inner.get("body")
    if isinstance(body, list):
        items = body
    elif isinstance(body, dict):
        items = body.get("value", [])
        if not isinstance(items, list):
            items = [body] if body else []
    else:
        items = []

    # --- cursor (LastPollInformation from Location header) ---------------
    new_cursor: str | None = None
    headers = inner.get("headers", {})
    location = headers.get("Location") or headers.get("location")
    if location:
        parsed = parse_qs(urlparse(location).query)
        lpi = parsed.get("LastPollInformation")
        if lpi:
            new_cursor = lpi[0]

    # --- retry_after -----------------------------------------------------
    retry_after: int | None = None
    ra_raw = headers.get("Retry-After") or headers.get("retry-after")
    if ra_raw is not None:
        try:
            retry_after = int(ra_raw)
        except (ValueError, TypeError):
            pass

    return PollResult(
        status=status,
        items=items,
        cursor=new_cursor,
        retry_after=retry_after,
    )