import logging
import azure.functions as func
import azure.functions_connectors as fc
from azure.functions_connectors import Office365Email, Office365Event

app = func.FunctionApp()
connectors = fc.FunctionsConnectors(app)


@connectors.office365.new_email_trigger(
    connection_id="%OFFICE365_CONNECTION_ID%",
    folder="Inbox",
)
async def on_new_email(email: Office365Email):
    logging.info(f"[NEW EMAIL] From: {email.sender}")
    logging.info(f"[NEW EMAIL] Subject: {email.subject}")


@connectors.office365.flagged_email_trigger(
    connection_id="%OFFICE365_CONNECTION_ID%",
    folder="Inbox",
)
async def on_flagged_email(email: Office365Email):
    logging.info(f"[FLAGGED EMAIL] Subject: {email.subject}")


@connectors.office365.new_event_trigger(
    connection_id="%OFFICE365_CONNECTION_ID%",
    calendar_id="Calendar",
)
async def on_new_event(event: Office365Event):
    logging.info(f"[NEW EVENT] Subject: {event.subject}")
    logging.info(f"[NEW EVENT] Start: {event.start}")
    logging.info(f"[NEW EVENT] End: {event.end}")
    logging.info(f"[NEW EVENT] Location: {event.location}")


@connectors.office365.event_changed_trigger(
    connection_id="%OFFICE365_CONNECTION_ID%",
    calendar_id="Calendar",
    incoming_days=7,
)
async def on_event_changed(event: Office365Event):
    logging.info(f"[EVENT CHANGED] Subject: {event.subject}")
    logging.info(f"[EVENT CHANGED] Start: {event.start}")
