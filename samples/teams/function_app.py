"""Teams client sample — list channels and recent messages on a timer.

Teams polling triggers are not currently supported due to a connector-side
bug. This sample demonstrates using the Teams client on a timer as a
workaround to periodically check for new messages.
"""

import logging
import azure.functions as func
import azure.functions_connectors as fc

app = func.FunctionApp()
connectors = fc.FunctionsConnectors(app)


@app.timer_trigger(schedule="0 */5 * * * *", arg_name="timer",
                   run_on_startup=True)
async def check_teams_messages(timer: func.TimerRequest):
    """Periodically check a Teams channel for new messages."""
    client = connectors.teams.get_client("%TEAMS_CONNECTION_ID%")

    # List channels in a team
    channels = await client.list_channels("%TEAMS_TEAM_ID%")
    for ch in channels:
        logging.info(f"Channel: {ch.get('displayName')}")

    # Get recent messages from a specific channel
    messages = await client.get_messages_from_channel(
        "%TEAMS_TEAM_ID%", "%TEAMS_CHANNEL_ID%"
    )
    for msg in messages:
        sender = msg.get("from", {}).get("user", {}).get("displayName", "?")
        body = msg.get("body", {}).get("content", "")[:80]
        logging.info(f"[MSG] {sender}: {body}")
