"""Custom action-based polling helpers for connectors."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlparse

from ._client import ConnectorClient, ConnectorError
from ._models import PollResult

logger = logging.getLogger(__name__)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _extract_cursor_datetime(cursor: str | None) -> datetime | None:
    if not cursor:
        return None
    try:
        data = json.loads(cursor)
        if isinstance(data, dict):
            return _parse_datetime(data.get("createdDateTime"))
    except (json.JSONDecodeError, TypeError):
        pass
    return _parse_datetime(cursor)


def _cursor_json(created_date_time: str | None) -> str | None:
    if not created_date_time:
        return None
    return json.dumps({"createdDateTime": created_date_time})


def _extract_items_and_next_link(response_body: dict) -> tuple[list[dict], str | None]:
    body = response_body.get("body")
    if isinstance(body, dict):
        value = body.get("value")
        items = value if isinstance(value, list) else []
        next_link = body.get("@odata.nextLink")
        return items, next_link if isinstance(next_link, str) else None

    value = response_body.get("value")
    items = value if isinstance(value, list) else []
    next_link = response_body.get("@odata.nextLink")
    return items, next_link if isinstance(next_link, str) else None


def _extract_next_invoke_params(
    next_link: str,
    team_id: str,
    channel_id: str,
) -> tuple[str, dict[str, str]]:
    parsed = urlparse(next_link)
    path = parsed.path
    marker = "/beta/teams/"
    marker_index = path.find(marker)
    if marker_index >= 0:
        path = path[marker_index:]
    else:
        path = f"/beta/teams/{team_id}/channels/{channel_id}/messages"
    queries = {k: v for k, v in parse_qsl(parsed.query, keep_blank_values=True)}
    return path, queries


def _is_user_message(item: dict) -> bool:
    return item.get("messageType") == "message"


def _contains_mention(item: dict) -> bool:
    body = item.get("body")
    if not isinstance(body, dict):
        return False
    content = body.get("content")
    if not isinstance(content, str):
        return False
    return "<at" in content.lower()


def poll_channel_messages(
    connection_id: str,
    team_id: str,
    channel_id: str,
    cursor: str | None = None,
    mention_only: bool = False,
) -> PollResult:
    """Poll Teams channel messages through action dynamicInvoke."""
    client = ConnectorClient(connection_id)
    path = f"/beta/teams/{team_id}/channels/{channel_id}/messages"
    queries: dict[str, str] = {"$top": "50"}

    prior_dt = _extract_cursor_datetime(cursor)
    new_items: list[dict] = []
    newest_seen: str | None = None

    try:
        while True:
            response_body = client._invoke_sync("GET", path, queries, None)
            page_items, next_link = _extract_items_and_next_link(response_body)

            if newest_seen is None:
                for item in page_items:
                    created = item.get("createdDateTime")
                    if isinstance(created, str) and created:
                        newest_seen = created
                        break

            if prior_dt is None:
                return PollResult(status=202, items=[], cursor=_cursor_json(newest_seen))

            all_newer = True
            for item in page_items:
                created_raw = item.get("createdDateTime")
                created_dt = _parse_datetime(created_raw) if isinstance(created_raw, str) else None
                if created_dt is None:
                    continue
                if created_dt <= prior_dt:
                    all_newer = False
                    break
                if _is_user_message(item) and (not mention_only or _contains_mention(item)):
                    new_items.append(item)

            if not page_items:
                break
            if not all_newer:
                break
            if not next_link:
                break

            path, queries = _extract_next_invoke_params(next_link, team_id, channel_id)

    except ConnectorError as exc:
        logger.warning("Teams action poll failed: %s", exc)
        return PollResult(status=500, items=[])
    except Exception:
        logger.warning("Teams action poll failed unexpectedly", exc_info=True)
        return PollResult(status=500, items=[])

    new_items.reverse()
    next_cursor = _cursor_json(newest_seen) or cursor
    return PollResult(status=200, items=new_items, cursor=next_cursor)



def _format_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _extract_calendar_cursor(cursor: str | None) -> datetime | None:
    if not cursor:
        return None
    try:
        data = json.loads(cursor)
        if isinstance(data, dict):
            ts = data.get("timestamp")
            if isinstance(ts, str):
                return _parse_datetime(ts)
    except (json.JSONDecodeError, TypeError):
        pass
    return _parse_datetime(cursor)


def _calendar_cursor_json(timestamp: str | None) -> str | None:
    if not timestamp:
        return None
    return json.dumps({"timestamp": timestamp})


def _extract_calendar_items_and_next_token(response_body: dict) -> tuple[list[dict], str | None]:
    body = response_body.get("body") if isinstance(response_body, dict) else None
    source = body if isinstance(body, dict) else response_body
    if not isinstance(source, dict):
        return [], None

    items = source.get("items")
    next_token = source.get("nextPageToken")
    return (
        items if isinstance(items, list) else [],
        next_token if isinstance(next_token, str) and next_token else None,
    )


def poll_calendar_events(
    connection_id: str,
    calendar_id: str,
    cursor: str | None = None,
    detect_updates: bool = False,
) -> PollResult:
    """Poll Google Calendar events through action dynamicInvoke."""
    client = ConnectorClient(connection_id)
    path = f"calendars/{calendar_id}/events"

    now_utc = datetime.now(timezone.utc)
    prior_dt = _extract_calendar_cursor(cursor)
    first_poll = prior_dt is None

    time_min_dt = prior_dt or (now_utc - timedelta(hours=24))
    time_min = _format_utc(time_min_dt)

    queries: dict[str, str] = {"timeMin": time_min}
    if detect_updates:
        if prior_dt is not None:
            queries["updatedMin"] = _format_utc(prior_dt)
    else:
        queries["orderBy"] = "startTime"
        queries["singleEvents"] = "true"

    seen_items: list[dict] = []

    try:
        while True:
            response_body = client._invoke_sync("GET", path, queries, None)
            page_items, next_page_token = _extract_calendar_items_and_next_token(response_body)
            if first_poll:
                return PollResult(status=202, items=[], cursor=_calendar_cursor_json(_format_utc(now_utc)))

            seen_items.extend(page_items)

            if not next_page_token:
                break

            queries = {**queries, "pageToken": next_page_token}

        if prior_dt is None:
            return PollResult(status=200, items=[], cursor=cursor)

        filtered_items: list[dict] = []
        newest_dt = prior_dt
        cursor_field = "updated" if detect_updates else "created"

        for item in seen_items:
            raw_ts = item.get(cursor_field)
            if not isinstance(raw_ts, str):
                continue
            item_dt = _parse_datetime(raw_ts)
            if item_dt is None or item_dt <= prior_dt:
                continue

            filtered_items.append(item)
            if item_dt > newest_dt:
                newest_dt = item_dt

        filtered_items.sort(
            key=lambda event: _parse_datetime(event.get(cursor_field))
            or datetime.min.replace(tzinfo=timezone.utc)
        )

        next_cursor = _calendar_cursor_json(_format_utc(newest_dt)) if newest_dt else cursor
        return PollResult(status=200, items=filtered_items, cursor=next_cursor)

    except ConnectorError as exc:
        logger.warning("Google Calendar action poll failed: %s", exc)
        return PollResult(status=500, items=[])
    except Exception:
        logger.warning("Google Calendar action poll failed unexpectedly", exc_info=True)
        return PollResult(status=500, items=[])
