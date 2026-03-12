"""Teams connector item models, action-based triggers, and client factory."""

from __future__ import annotations

from typing import Callable, TYPE_CHECKING

from .._models import ConnectorItem

if TYPE_CHECKING:
    from .._decorator import FunctionsConnectors


class TeamsMessage(ConnectorItem):
    """Typed wrapper for a Teams message item.

    Supports both camelCase and PascalCase keys.
    """

    @property
    def id(self) -> str:
        return self.get("id") or self.get("Id", "")

    @property
    def body(self):
        return self.get("body") or self.get("Body", "")

    @property
    def body_preview(self) -> str:
        return self.get("bodyPreview") or self.get("BodyPreview", "")

    @property
    def sender(self) -> str:
        value = self.get("from")
        if value is None:
            value = self.get("From", "")
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            user = value.get("user") or value.get("User")
            if isinstance(user, dict):
                return (
                    user.get("displayName")
                    or user.get("DisplayName")
                    or user.get("email")
                    or user.get("Email")
                    or user.get("id")
                    or user.get("Id", "")
                )
            if user is not None:
                return str(user)
            return ""
        return str(value)

    @property
    def created_at(self) -> str:
        return self.get("createdDateTime") or self.get("CreatedDateTime", "")

    @property
    def message_type(self) -> str:
        return self.get("messageType") or self.get("MessageType", "")

    @property
    def subject(self) -> str:
        return self.get("subject") or self.get("Subject", "")

    @property
    def importance(self) -> str:
        return self.get("importance") or self.get("Importance", "")

    @property
    def web_url(self) -> str:
        return self.get("webUrl") or self.get("WebUrl", "")

    @property
    def channel_identity(self):
        return self.get("channelIdentity") or self.get("ChannelIdentity", {})

    @property
    def attachments(self) -> list:
        return self.get("attachments") or self.get("Attachments", [])


class TeamsChannel(ConnectorItem):
    """Typed wrapper for a Teams channel item."""

    @property
    def id(self) -> str:
        return self.get("id") or self.get("Id", "")

    @property
    def name(self) -> str:
        return self.get("displayName") or self.get("DisplayName", "")

    @property
    def description(self) -> str:
        return self.get("description") or self.get("Description", "")

    @property
    def membership_type(self) -> str:
        return self.get("membershipType") or self.get("MembershipType", "")


class TeamsTriggers:
    """Teams typed triggers and client factory.

    Triggers use action-based polling via ``get_messages`` to avoid broken
    native Teams polling trigger endpoints.
    """

    def __init__(self, parent: FunctionsConnectors) -> None:
        self._parent = parent

    def get_client(self, connection_id: str) -> "TeamsClient":
        from .._client import ConnectorClient
        from .._clients.teams import TeamsClient

        return TeamsClient(ConnectorClient(connection_id))

    def new_channel_message_trigger(
        self,
        connection_id: str,
        team_id: str,
        channel_id: str,
    ) -> Callable:
        """Trigger when a new post is made in a Teams channel."""
        from functools import partial

        from .._env import resolve_value
        from .._poll_action import poll_channel_messages

        resolved_conn = resolve_value(connection_id)
        resolved_team = resolve_value(team_id)
        resolved_channel = resolve_value(channel_id)
        # Bind all args except cursor — poller calls poll_fn(connection_id, cursor)
        # but connection_id is already baked in, so wrap to only take cursor.
        _bound = partial(
            poll_channel_messages,
            connection_id=resolved_conn,
            team_id=resolved_team,
            channel_id=resolved_channel,
        )
        poll_fn = lambda conn_id, cur: _bound(cursor=cur)

        return self._parent.generic_trigger(
            connection_id=connection_id,
            trigger_path=f"/action-poll/teams/{resolved_team}/channels/{resolved_channel}/messages",
            trigger_queries={},
            poll_function=poll_fn,
        )

    def channel_mention_trigger(
        self,
        connection_id: str,
        team_id: str,
        channel_id: str,
    ) -> Callable:
        """Trigger when you are @mentioned in a Teams channel post."""
        from functools import partial

        from .._env import resolve_value
        from .._poll_action import poll_channel_messages

        resolved_conn = resolve_value(connection_id)
        resolved_team = resolve_value(team_id)
        resolved_channel = resolve_value(channel_id)
        _bound = partial(
            poll_channel_messages,
            connection_id=resolved_conn,
            team_id=resolved_team,
            channel_id=resolved_channel,
            mention_only=True,
        )
        poll_fn = lambda conn_id, cur: _bound(cursor=cur)

        return self._parent.generic_trigger(
            connection_id=connection_id,
            trigger_path=f"/action-poll/teams/{resolved_team}/channels/{resolved_channel}/mentions",
            trigger_queries={},
            poll_function=poll_fn,
        )


# Backward-compatible alias for the original typo'ed class name.
TeamsTrigers = TeamsTriggers
