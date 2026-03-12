"""Teams sample — channel message triggers with auto-reply and client usage."""

import logging
import os

import azure.functions as func
import azure.functions_connectors as fc
from azure.functions_connectors import TeamsMessage

app = func.FunctionApp()
connectors = fc.FunctionsConnectors(app)


@connectors.teams.new_channel_message_trigger(
    connection_id="%TEAMS_CONNECTION_ID%",
    team_id="%TEAMS_TEAM_ID%",
    channel_id="%TEAMS_CHANNEL_ID%",
)
async def on_channel_message(msg: TeamsMessage):
    """Fires when a new post is made in a Teams channel. Replies to it."""
    logging.info(f"[CHANNEL MSG] From: {msg.sender}, ID: {msg.id}")
    body = msg.body
    content = body.get("content", "") if isinstance(body, dict) else str(body)
    logging.info(f"[CHANNEL MSG] Content: {content[:200]}")

    # Reply to the message using the Teams client
    client = connectors.teams.get_client("%TEAMS_CONNECTION_ID%")
    await client.reply_to_message(
        team_id=os.environ["TEAMS_TEAM_ID"],
        channel_id=os.environ["TEAMS_CHANNEL_ID"],
        message_id=msg.id,
        body=f"Thanks for your message, {msg.sender}! 🤖",
    )
    logging.info(f"[CHANNEL MSG] Replied to message {msg.id}")


@connectors.teams.channel_mention_trigger(
    connection_id="%TEAMS_CONNECTION_ID%",
    team_id="%TEAMS_TEAM_ID%",
    channel_id="%TEAMS_CHANNEL_ID%",
)
async def on_mention(msg: TeamsMessage):
    """Fires when you are @mentioned in a Teams channel post."""
    logging.info(f"[MENTIONED] From: {msg.sender}")
    body = msg.body
    content = body.get("content", "") if isinstance(body, dict) else str(body)
    logging.info(f"[MENTIONED] Content: {content[:200]}")
