"""Gmail connector item model and client factory.

Gmail supports actions only (send, reply, get, trash, delete). No polling
triggers are available because the connector has no list emails action.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .._models import ConnectorItem

if TYPE_CHECKING:
    from .._decorator import FunctionsConnectors


class GmailEmail(ConnectorItem):
    """Typed wrapper for a Gmail email item payload."""

    @property
    def id(self) -> str:
        return self.get("Id") or self.get("id", "")

    @property
    def subject(self) -> str:
        return self.get("Subject") or self.get("subject", "")

    @property
    def body(self) -> str:
        return self.get("Body") or self.get("body", "")

    @property
    def from_address(self) -> str:
        return self.get("From") or self.get("from", "")

    @property
    def to(self):
        return self.get("To") or self.get("to", "")

    @property
    def cc(self):
        return self.get("Cc") or self.get("cc")

    @property
    def bcc(self):
        return self.get("Bcc") or self.get("bcc")

    @property
    def date_time_received(self) -> str:
        return self.get("DateTimeReceived") or self.get("dateTimeReceived", "")

    @property
    def is_read(self) -> bool:
        return self.get("IsRead") or self.get("isRead", False)

    @property
    def has_attachment(self) -> bool:
        return self.get("HasAttachment") or self.get("hasAttachment", False)

    @property
    def importance(self) -> str:
        return self.get("Importance") or self.get("importance", "")


class GmailTriggers:
    """Gmail typed client factory.

    Gmail is action-only and does not provide polling trigger endpoints.
    """

    def __init__(self, parent: FunctionsConnectors) -> None:
        self._parent = parent

    def get_client(self, connection_id: str) -> "GmailClient":
        """Get a typed Gmail client for calling actions."""
        from .._client import ConnectorClient
        from .._clients.gmail import GmailClient

        return GmailClient(ConnectorClient(connection_id))
