"""Strongly-typed Office 365 connector triggers and item models."""

from __future__ import annotations

from typing import Callable, TYPE_CHECKING

from .._models import ConnectorItem

if TYPE_CHECKING:
    from .._decorator import FunctionsConnectors


# ---------------------------------------------------------------------------
# Item models
# ---------------------------------------------------------------------------

class Office365Email(ConnectorItem):
    """Typed wrapper for an Office 365 email item.

    Supports both camelCase (v3 trigger) and PascalCase (v1 trigger) keys.
    """

    @property
    def id(self) -> str:
        return self.get("id") or self.get("Id", "")

    @property
    def subject(self) -> str:
        return self.get("subject") or self.get("Subject", "")

    @property
    def sender(self) -> str:
        return self.get("from") or self.get("From", "")

    @property
    def to(self) -> str:
        return self.get("toRecipients") or self.get("To", "")

    @property
    def cc(self) -> str | None:
        return self.get("ccRecipients") or self.get("Cc")

    @property
    def bcc(self) -> str | None:
        return self.get("bccRecipients") or self.get("Bcc")

    @property
    def body(self) -> str:
        return self.get("body") or self.get("Body", "")

    @property
    def body_preview(self) -> str:
        return self.get("bodyPreview") or self.get("BodyPreview", "")

    @property
    def importance(self) -> str:
        return self.get("importance") or self.get("Importance", "")

    @property
    def received_at(self) -> str:
        return self.get("receivedDateTime") or self.get("DateTimeReceived", "")

    @property
    def has_attachment(self) -> bool:
        return self.get("hasAttachments") or self.get("HasAttachment", False)

    @property
    def is_read(self) -> bool:
        return self.get("isRead") or self.get("IsRead", False)

    @property
    def is_html(self) -> bool:
        return self.get("isHtml") or self.get("IsHtml", False)

    @property
    def internet_message_id(self) -> str:
        return self.get("internetMessageId") or self.get("InternetMessageId", "")

    @property
    def conversation_id(self) -> str:
        return self.get("conversationId") or self.get("ConversationId", "")

    @property
    def attachments(self) -> list:
        return self.get("attachments") or self.get("Attachments", [])

    @property
    def reply_to(self) -> str | None:
        return self.get("replyTo") or self.get("ReplyTo")


class Office365Event(ConnectorItem):
    """Typed wrapper for an Office 365 calendar event item.

    Supports both camelCase and PascalCase keys.
    """

    @property
    def id(self) -> str:
        return self.get("id") or self.get("Id", "")

    @property
    def subject(self) -> str:
        return self.get("subject") or self.get("Subject", "")

    @property
    def body(self) -> str:
        return self.get("body") or self.get("Body", "")

    @property
    def body_preview(self) -> str:
        return self.get("bodyPreview") or self.get("BodyPreview", "")

    @property
    def start(self) -> str:
        return self.get("start") or self.get("Start", "")

    @property
    def end(self) -> str:
        return self.get("end") or self.get("End", "")

    @property
    def location(self) -> str:
        return self.get("location") or self.get("Location", "")

    @property
    def organizer(self) -> str:
        return self.get("organizer") or self.get("Organizer", "")

    @property
    def is_all_day(self) -> bool:
        return self.get("isAllDay") or self.get("IsAllDay", False)

    @property
    def show_as(self) -> str:
        return self.get("showAs") or self.get("ShowAs", "")

    @property
    def attendees(self) -> list:
        return self.get("attendees") or self.get("Attendees", [])

    @property
    def is_reminder_on(self) -> bool:
        return self.get("isReminderOn") or self.get("IsReminderOn", False)

    @property
    def recurrence(self) -> str | None:
        return self.get("recurrence") or self.get("Recurrence")


# ---------------------------------------------------------------------------
# Trigger builder
# ---------------------------------------------------------------------------

class Office365Triggers:
    """Strongly-typed Office 365 trigger decorators.

    Accessed via ``connectors.office365``.
    """

    def __init__(self, parent: FunctionsConnectors) -> None:
        self._parent = parent

    def new_email_trigger(
        self,
        connection_id: str,
        folder: str = "Inbox",
        from_filter: str | None = None,
        to_filter: str | None = None,
        cc_filter: str | None = None,
        importance: str | None = None,
        subject_filter: str | None = None,
        include_attachments: bool = False,
        only_with_attachments: bool = False,
    ) -> Callable:
        """Trigger when a new email arrives."""
        queries: dict[str, str] = {"folderPath": folder}
        if from_filter:
            queries["from"] = from_filter
        if to_filter:
            queries["to"] = to_filter
        if cc_filter:
            queries["cc"] = cc_filter
        if importance:
            queries["importance"] = importance
        if subject_filter:
            queries["subjectFilter"] = subject_filter
        if include_attachments:
            queries["includeAttachments"] = "true"
        if only_with_attachments:
            queries["fetchOnlyWithAttachment"] = "true"

        return self._parent.generic_trigger(
            connection_id=connection_id,
            trigger_path="/v3/Mail/OnNewEmail",
            trigger_queries=queries,
        )

    def flagged_email_trigger(
        self,
        connection_id: str,
        folder: str = "Inbox",
        from_filter: str | None = None,
        to_filter: str | None = None,
        importance: str | None = None,
        subject_filter: str | None = None,
    ) -> Callable:
        """Trigger when an email is flagged."""
        queries: dict[str, str] = {"folderPath": folder}
        if from_filter:
            queries["from"] = from_filter
        if to_filter:
            queries["to"] = to_filter
        if importance:
            queries["importance"] = importance
        if subject_filter:
            queries["subjectFilter"] = subject_filter

        return self._parent.generic_trigger(
            connection_id=connection_id,
            trigger_path="/v4/Mail/OnFlaggedEmail",
            trigger_queries=queries,
        )

    def new_event_trigger(
        self,
        connection_id: str,
        calendar_id: str = "Calendar",
    ) -> Callable:
        """Trigger when a new calendar event is created."""
        return self._parent.generic_trigger(
            connection_id=connection_id,
            trigger_path=f"/datasets/calendars/v3/tables/{calendar_id}/onnewitems",
            trigger_queries={},
        )

    def event_changed_trigger(
        self,
        connection_id: str,
        calendar_id: str = "Calendar",
        incoming_days: int | None = None,
        past_days: int | None = None,
    ) -> Callable:
        """Trigger when a calendar event is added, updated, or deleted."""
        queries: dict[str, str] = {}
        if incoming_days is not None:
            queries["incomingDays"] = str(incoming_days)
        if past_days is not None:
            queries["pastDays"] = str(past_days)

        return self._parent.generic_trigger(
            connection_id=connection_id,
            trigger_path=f"/datasets/calendars/v3/tables/{calendar_id}/onchangeditems",
            trigger_queries=queries,
        )
