import logging
import azure.functions as func
import azure.functions_connectors as fc

app = func.FunctionApp()


@fc.generic_connection_trigger(
    app,
    connection_id="%OFFICE365_CONNECTION_ID%",
    trigger_path="/Mail/OnNewEmail",
    trigger_queries={"folderPath": "Inbox"},
)
async def on_new_email(item: dict):
    """Log new emails."""
    subject = item.get("Subject", "(no subject)")
    sender = item.get("From", "Unknown")
    preview = item.get("BodyPreview", "")[:100]
    logging.info(f"[Handler 1] New email from {sender}: {subject}")
    if preview:
        logging.info(f"[Handler 1]   Preview: {preview}")


@fc.generic_connection_trigger(
    app,
    connection_id="%OFFICE365_CONNECTION_ID%",
    trigger_path="/Mail/OnNewEmail",
    trigger_queries={"folderPath": "Inbox"},
)
async def on_new_email_audit(item: dict):
    """Audit log for new emails — demonstrates multiple handlers on the same trigger."""
    subject = item.get("Subject", "(no subject)")
    received = item.get("DateTimeReceived", "unknown")
    logging.info(f"[Handler 2] AUDIT: '{subject}' received at {received}")


fc.register_connector_triggers(app)
