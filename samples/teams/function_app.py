"""Teams sample — channel message triggers and client usage."""

import logging

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
    """Fires when a new post is made in a Teams channel."""
    logging.info(f"[CHANNEL MSG] From: {msg.sender}")
    logging.info(f"[CHANNEL MSG] Body: {msg.body_preview}")


@connectors.teams.channel_mention_trigger(
    connection_id="%TEAMS_CONNECTION_ID%",
    team_id="%TEAMS_TEAM_ID%",
    channel_id="%TEAMS_CHANNEL_ID%",
)
async def on_mention(msg: TeamsMessage):
    """Fires when you are @mentioned in a Teams channel post."""
    logging.info(f"[MENTIONED] From: {msg.sender}")
    logging.info(f"[MENTIONED] Body: {msg.body_preview}")


@app.timer_trigger(schedule="0 */10 * * * *", arg_name="timer",
                   run_on_startup=True)
async def query_teams(timer: func.TimerRequest):
    """Demonstrate Teams client usage."""
    client = connectors.teams.get_client("%TEAMS_CONNECTION_ID%")
    channels = await client.list_channels("%TEAMS_TEAM_ID%")
    for ch in channels:
        logging.info(f"Channel: {ch.get('displayName')}")
