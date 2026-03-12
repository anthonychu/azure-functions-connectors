"""Typed Gmail client for calling connector actions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .._env import resolve_value

if TYPE_CHECKING:
    from .._client import ConnectorClient


class GmailClient:
    """Typed client for Gmail connector actions."""

    def __init__(self, client: ConnectorClient) -> None:
        self._client = client

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: str | None = None,
        bcc: str | None = None,
        importance: str = "Normal",
    ) -> dict:
        """Send an email."""
        payload: dict = {
            "To": to,
            "Subject": subject,
            "Body": body,
            "Importance": importance,
        }
        if cc is not None:
            payload["Cc"] = cc
        if bcc is not None:
            payload["Bcc"] = bcc
        return await self._client.invoke("POST", "/v2/Mail", body=payload)

    async def reply_to(
        self,
        message_id: str,
        body: str | None = None,
        to: str | None = None,
        cc: str | None = None,
        bcc: str | None = None,
        reply_all: bool = False,
    ) -> dict:
        """Reply to an email."""
        resolved_message_id = resolve_value(message_id)
        payload: dict = {"ReplyAll": reply_all}
        if body is not None:
            payload["Body"] = body
        if to is not None:
            payload["To"] = to
        if cc is not None:
            payload["Cc"] = cc
        if bcc is not None:
            payload["Bcc"] = bcc
        return await self._client.invoke(
            "POST",
            f"/v2/Mail/{resolved_message_id}/ReplyTo",
            body=payload,
        )

    async def get_email(self, message_id: str, include_attachments: bool = False) -> dict:
        """Get a single email by ID."""
        resolved_message_id = resolve_value(message_id)
        return await self._client.invoke(
            "GET",
            f"/Mail/{resolved_message_id}",
            queries={"includeAttachments": str(include_attachments).lower()},
        )

    async def trash_email(self, message_id: str) -> dict:
        """Move an email to trash."""
        resolved_message_id = resolve_value(message_id)
        return await self._client.invoke("POST", f"/Mail/{resolved_message_id}/trash")

    async def delete_email(self, message_id: str) -> dict:
        """Delete an email permanently."""
        resolved_message_id = resolve_value(message_id)
        return await self._client.invoke("DELETE", f"/Mail/{resolved_message_id}")
