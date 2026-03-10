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
    """Fires when a new message is posted in a Teams channel."""
    logging.info(f"[CHANNEL MSG] From: {msg.sender}")
    logging.info(f"[CHANNEL MSG] Body: {msg.body_preview}")


@connectors.teams.channel_mention_trigger(
    connection_id="%TEAMS_CONNECTION_ID%",
    team_id="%TEAMS_TEAM_ID%",
    channel_id="%TEAMS_CHANNEL_ID%",
)
async def on_mention(msg: TeamsMessage):
    """Fires when you are @mentioned in a Teams channel."""
    logging.info(f"[MENTIONED] From: {msg.sender}")
    logging.info(f"[MENTIONED] Body: {msg.body_preview}")
