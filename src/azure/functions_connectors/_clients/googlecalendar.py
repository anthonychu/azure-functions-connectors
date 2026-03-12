"""Typed Google Calendar client for calling connector actions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .._env import resolve_value

if TYPE_CHECKING:
    from .._client import ConnectorClient


class GoogleCalendarClient:
    """Typed client for Google Calendar connector actions."""

    def __init__(self, client: ConnectorClient) -> None:
        self._client = client

    async def list_calendars(self) -> dict:
        """List calendars available to the current user."""
        return await self._client.invoke("GET", "users/me/calendarList")

    async def list_events(
        self,
        calendar_id: str,
        time_min: str | None = None,
        time_max: str | None = None,
        q: str | None = None,
        updated_min: str | None = None,
        max_results: int | None = None,
    ) -> dict:
        """List events for a calendar with optional query filters."""
        resolved_calendar = resolve_value(calendar_id)
        queries: dict[str, str] = {}
        if time_min:
            queries["timeMin"] = time_min
        if time_max:
            queries["timeMax"] = time_max
        if q:
            queries["q"] = q
        if updated_min:
            queries["updatedMin"] = updated_min
        if max_results is not None:
            queries["maxResults"] = str(max_results)

        return await self._client.invoke(
            "GET",
            f"calendars/{resolved_calendar}/events",
            queries=queries,
        )

    async def get_event(self, calendar_id: str, event_id: str) -> dict:
        """Get a single event by ID."""
        resolved_calendar = resolve_value(calendar_id)
        resolved_event = resolve_value(event_id)
        return await self._client.invoke(
            "GET",
            f"calendars/{resolved_calendar}/events/{resolved_event}",
        )

    async def create_event(
        self,
        calendar_id: str,
        summary: str,
        start: str,
        end: str,
        description: str | None = None,
        location: str | None = None,
        attendees: list[dict] | None = None,
    ) -> dict:
        """Create an event in a calendar."""
        resolved_calendar = resolve_value(calendar_id)
        payload: dict = {
            "summary": summary,
            "start": start,
            "end": end,
        }
        if description:
            payload["description"] = description
        if location:
            payload["location"] = location
        if attendees is not None:
            payload["attendees"] = attendees

        return await self._client.invoke(
            "POST",
            f"calendars/{resolved_calendar}/events",
            body=payload,
        )

    async def update_event(self, calendar_id: str, event_id: str, **fields) -> dict:
        """Update an event by ID using the provided fields."""
        resolved_calendar = resolve_value(calendar_id)
        resolved_event = resolve_value(event_id)
        return await self._client.invoke(
            "PUT",
            f"calendars/{resolved_calendar}/events/{resolved_event}",
            body=fields,
        )

    async def delete_event(self, calendar_id: str, event_id: str) -> dict:
        """Delete an event by ID."""
        resolved_calendar = resolve_value(calendar_id)
        resolved_event = resolve_value(event_id)
        return await self._client.invoke(
            "DELETE",
            f"calendars/{resolved_calendar}/events/{resolved_event}",
        )
