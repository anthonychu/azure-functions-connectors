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
    # The connector returns PascalCase keys: Subject, From, BodyPreview, etc.
    subject = item.get("Subject", "(no subject)")
    sender = item.get("From", "Unknown")
    preview = item.get("BodyPreview", "")[:100]
    logging.info(f"New email from {sender}: {subject}")
    if preview:
        logging.info(f"  Preview: {preview}")


fc.register_connector_triggers(app)
