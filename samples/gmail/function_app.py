"""Gmail sample — send and manage emails."""

import logging
import os

import azure.functions as func
import azure.functions_connectors as fc

app = func.FunctionApp()
connectors = fc.FunctionsConnectors(app)


@app.timer_trigger(schedule="0 */10 * * * *", arg_name="timer", run_on_startup=True)
async def gmail_send_sample(timer: func.TimerRequest):
    """Timer-driven Gmail sample for sending and managing messages."""
    client = connectors.gmail.get_client("%GMAIL_CONNECTION_ID%")

    result = await client.send_email(
        to=os.environ["GMAIL_SEND_TO"],
        subject="Hello from Azure Functions Connectors",
        body="This is a Gmail connector sample email.",
    )
    logging.info("[GMAIL SEND] Sent email result: %s", result)

    # Additional usage examples:
    # message = await client.get_email(message_id="<message-id>")
    # await client.reply_to(message_id="<message-id>", body="Thanks!")
