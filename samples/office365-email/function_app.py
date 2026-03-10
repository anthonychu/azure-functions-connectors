import logging
import azure.functions as func
import azure.functions.connector_triggers as ct

app = func.FunctionApp()


@ct.generic_connection_trigger(
    connection_id="%OFFICE365_CONNECTION_ID%",
    trigger_path="/Mail/OnNewEmail",
    trigger_queries={"folderPath": "Inbox"},
)
async def on_new_email(item: dict):
    subject = item.get("subject", "(no subject)")
    sender = item.get("from", {}).get("emailAddress", {}).get("name", "Unknown")
    logging.info(f"New email from {sender}: {subject}")


ct.register_connector_triggers(app)
