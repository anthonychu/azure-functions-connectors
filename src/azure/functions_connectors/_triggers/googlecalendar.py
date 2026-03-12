"""Google Calendar connector item model, action-based triggers, and client factory."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from .._models import ConnectorItem

if TYPE_CHECKING:
    from .._decorator import FunctionsConnectors


class GoogleCalendarEvent(ConnectorItem):
    """Typed wrapper for a Google Calendar event item."""

    @property
    def id(self) -> str:
        return self.get("id", "")

    @property
    def summary(self) -> str:
        return self.get("summary", "")

    @property
    def description(self) -> str:
        return self.get("description", "")

    @property
    def location(self) -> str:
        return self.get("location", "")

    @property
    def start(self):
        return self.get("start", "")

    @property
    def end(self):
        return self.get("end", "")

    @property
    def status(self) -> str:
        return self.get("status", "")

    @property
    def creator(self) -> str:
        value = self.get("creator")
        if isinstance(value, dict):
            return value.get("email", "")
        if isinstance(value, str):
            return value
        return ""

    @property
    def organizer(self) -> str:
        value = self.get("organizer")
        if isinstance(value, dict):
            return value.get("email", "")
        if isinstance(value, str):
            return value
        return ""

    @property
    def attendees(self) -> list:
        value = self.get("attendees")
        return value if isinstance(value, list) else []

    @property
    def html_link(self) -> str:
        return self.get("htmlLink", "")

    @property
    def created_at(self) -> str:
        return self.get("created", "")

    @property
    def updated_at(self) -> str:
        return self.get("updated", "")


class GoogleCalendarTriggers:
    """Google Calendar typed triggers and client factory."""

    def __init__(self, parent: FunctionsConnectors) -> None:
        self._parent = parent

    def get_client(self, connection_id: str) -> "GoogleCalendarClient":
        from .._client import ConnectorClient
        from .._clients.googlecalendar import GoogleCalendarClient

        return GoogleCalendarClient(ConnectorClient(connection_id))

    def new_event_trigger(
        self,
        connection_id: str,
        calendar_id: str,
        min_interval: int = 60,
        max_interval: int = 300,
    ) -> Callable:
        """Trigger when a new calendar event is created."""
        from functools import partial

        from .._env import resolve_value
        from .._poll_action import poll_calendar_events

        resolved_conn = resolve_value(connection_id)
        resolved_cal = resolve_value(calendar_id)
        _bound = partial(
            poll_calendar_events,
            connection_id=resolved_conn,
            calendar_id=resolved_cal,
        )
        poll_fn = lambda conn_id, cur: _bound(cursor=cur)

        return self._parent.generic_trigger(
            connection_id=connection_id,
            trigger_path=f"/action-poll/googlecalendar/{resolved_cal}/new-events",
            trigger_queries={},
            poll_function=poll_fn,
            min_interval=min_interval,
            max_interval=max_interval,
        )

    def updated_event_trigger(
        self,
        connection_id: str,
        calendar_id: str,
        min_interval: int = 60,
        max_interval: int = 300,
    ) -> Callable:
        """Trigger when an existing calendar event is updated."""
        from functools import partial

        from .._env import resolve_value
        from .._poll_action import poll_calendar_events

        resolved_conn = resolve_value(connection_id)
        resolved_cal = resolve_value(calendar_id)
        _bound = partial(
            poll_calendar_events,
            connection_id=resolved_conn,
            calendar_id=resolved_cal,
            detect_updates=True,
        )
        poll_fn = lambda conn_id, cur: _bound(cursor=cur)

        return self._parent.generic_trigger(
            connection_id=connection_id,
            trigger_path=f"/action-poll/googlecalendar/{resolved_cal}/updated-events",
            trigger_queries={},
            poll_function=poll_fn,
            min_interval=min_interval,
            max_interval=max_interval,
        )
