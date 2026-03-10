"""Typed Teams client for calling connector actions."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .._client import ConnectorClient


class TeamsClient:
    """Typed client for Teams connector actions.

    Usage::

        teams = TeamsClient(connector_client)
        await teams.post_message(team_id="team-id", channel_id="channel-id", body="Hello!")
    """

    def __init__(self, client: ConnectorClient) -> None:
        self._client = client

    # ── Messages ───────────────────────────────────────────────────────────

    async def post_message(
        self,
        team_id: str,
        channel_id: str,
        body: str,
        subject: str | None = None,
    ) -> dict:
        """Post a message to a channel."""
        return await self._client.invoke(
            "POST",
            f"/v3/beta/teams/{team_id}/channels/{channel_id}/messages",
            body={
                "body": {"content": body, "contentType": "html"},
                "subject": subject,
            },
        )

    async def reply_to_message(
        self,
        team_id: str,
        channel_id: str,
        message_id: str,
        body: str,
    ) -> dict:
        """Reply to a channel message."""
        return await self._client.invoke(
            "POST",
            f"/v2/beta/teams/{team_id}/channels/{channel_id}/messages/{message_id}/replies",
            body={"body": {"content": body, "contentType": "html"}},
        )

    async def get_messages(self, team_id: str, channel_id: str) -> list[dict]:
        """Get messages in a channel."""
        result = await self._client.invoke(
            "GET",
            f"/beta/teams/{team_id}/channels/{channel_id}/messages",
        )
        if isinstance(result, dict) and "value" in result:
            return result["value"]
        if isinstance(result, list):
            return result
        return []

    async def get_message_replies(
        self,
        team_id: str,
        channel_id: str,
        message_id: str,
        top: int = 20,
    ) -> list[dict]:
        """Get replies for a channel message."""
        result = await self._client.invoke(
            "GET",
            f"/v1.0/teams/{team_id}/channels/{channel_id}/messages/{message_id}/replies",
            queries={"$top": str(top)},
        )
        if isinstance(result, dict) and "value" in result:
            return result["value"]
        if isinstance(result, list):
            return result
        return []

    async def get_message_details(
        self,
        message_id: str,
        thread_type: str = "channel",
    ) -> dict:
        """Get details for a message by ID."""
        return await self._client.invoke(
            "POST",
            f"/beta/teams/messages/{message_id}/messageType/{thread_type}",
            body={},
        )

    # ── Channels ───────────────────────────────────────────────────────────

    async def list_channels(self, team_id: str) -> list[dict]:
        """List channels in a team."""
        result = await self._client.invoke("GET", f"/beta/groups/{team_id}/channels")
        if isinstance(result, dict) and "value" in result:
            return result["value"]
        if isinstance(result, list):
            return result
        return []

    async def list_all_channels(self, team_id: str) -> list[dict]:
        """List all channels in a team, including shared channels."""
        result = await self._client.invoke("GET", f"/beta/teams/{team_id}/allChannels")
        if isinstance(result, dict) and "value" in result:
            return result["value"]
        if isinstance(result, list):
            return result
        return []

    async def create_channel(
        self,
        team_id: str,
        name: str,
        description: str | None = None,
    ) -> dict:
        """Create a channel in a team."""
        return await self._client.invoke(
            "POST",
            f"/beta/groups/{team_id}/channels",
            body={"displayName": name, "description": description},
        )

    async def get_channel(self, team_id: str, channel_id: str) -> dict:
        """Get a channel by ID."""
        return await self._client.invoke(
            "GET",
            f"/beta/teams/{team_id}/channels/{channel_id}",
        )

    # ── Teams ──────────────────────────────────────────────────────────────

    async def list_teams(self) -> list[dict]:
        """List teams joined by the current user."""
        result = await self._client.invoke("GET", "/beta/me/joinedTeams")
        if isinstance(result, dict) and "value" in result:
            return result["value"]
        if isinstance(result, list):
            return result
        return []

    async def create_team(
        self,
        name: str,
        description: str,
        visibility: str = "Public",
    ) -> dict:
        """Create a team."""
        return await self._client.invoke(
            "POST",
            "/beta/teams",
            body={
                "displayName": name,
                "description": description,
                "visibility": visibility,
            },
        )

    async def get_team(self, team_id: str) -> dict:
        """Get a team by ID."""
        return await self._client.invoke("GET", f"/beta/teams/{team_id}")

    # ── Chats ──────────────────────────────────────────────────────────────

    async def list_chats(self, chat_type: str = "all") -> list[dict]:
        """List chats for the current user."""
        result = await self._client.invoke(
            "GET",
            f"/flowbot/actions/listchats/chattypes/{chat_type}/topic/all/expandmembers/false",
        )
        if isinstance(result, dict) and "value" in result:
            return result["value"]
        if isinstance(result, list):
            return result
        return []

    async def create_chat(self, members: str, topic: str | None = None) -> dict:
        """Create a chat."""
        return await self._client.invoke(
            "POST",
            "/beta/chats",
            body={"members": members, "topic": topic},
        )

    # ── Tags ───────────────────────────────────────────────────────────────

    async def list_tags(self, team_id: str) -> list[dict]:
        """List tags in a team."""
        result = await self._client.invoke("GET", f"/beta/teams/{team_id}/tags")
        if isinstance(result, dict) and "value" in result:
            return result["value"]
        if isinstance(result, list):
            return result
        return []

    async def create_tag(self, team_id: str, name: str, members: str) -> dict:
        """Create a team tag."""
        return await self._client.invoke(
            "POST",
            f"/beta/teams/{team_id}/tags",
            body={"displayName": name, "members": members},
        )

    async def delete_tag(self, team_id: str, tag_id: str) -> dict:
        """Delete a team tag."""
        return await self._client.invoke("DELETE", f"/beta/teams/{team_id}/tags/{tag_id}")

    async def add_member_to_tag(self, team_id: str, tag_id: str, user_id: str) -> dict:
        """Add a member to a team tag."""
        return await self._client.invoke(
            "POST",
            f"/beta/teams/{team_id}/tags/{tag_id}/members",
            body={"userId": user_id},
        )

    # ── Members ────────────────────────────────────────────────────────────

    async def add_member(self, team_id: str, user_id: str, owner: bool = False) -> dict:
        """Add a member to a team."""
        return await self._client.invoke(
            "POST",
            f"/beta/teams/{team_id}/members",
            body={"userId": user_id, "owner": owner},
        )

    async def get_mention_token(self, user_id: str) -> dict:
        """Get user details for building an @mention token."""
        return await self._client.invoke("GET", f"/v1.0/users/{user_id}")

    # ── Meetings ───────────────────────────────────────────────────────────

    async def create_meeting(
        self,
        subject: str,
        start: str,
        end: str,
        timezone: str,
        calendar_id: str = "Calendar",
        required_attendees: str | None = None,
        body: str | None = None,
    ) -> dict:
        """Create a Teams online meeting event in a calendar."""
        payload: dict = {
            "subject": subject,
            "start": {"dateTime": start, "timeZone": timezone},
            "end": {"dateTime": end, "timeZone": timezone},
            "isOnlineMeeting": True,
            "onlineMeetingProvider": "teamsForBusiness",
        }
        if required_attendees:
            payload["requiredAttendees"] = required_attendees
        if body:
            payload["body"] = body
        return await self._client.invoke(
            "POST",
            f"/v1.0/me/calendars/{calendar_id}/events",
            body=payload,
        )
