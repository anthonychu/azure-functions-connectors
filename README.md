# azure-functions-connector-triggers

Connector trigger bindings for Azure Functions (Python). Poll Azure managed connectors (Office 365, Salesforce, SharePoint, etc.) for new data using a simple decorator pattern.

## Features

- **Simple decorator API** — `@generic_connection_trigger(...)` on any function
- **Works with any Azure managed connector** — Office 365, Salesforce, SharePoint, Dynamics, and 500+ more
- **Automatic scale-out** — items dispatched via Storage Queue for parallel processing
- **Cursor-based polling** — only new items returned, no duplicates
- **Exponential backoff** — fast when active, quiet when idle
- **Config change detection** — automatically handles redeployments
- **Env var support** — `%VAR%` and `$VAR` syntax for connection IDs and queries

## Quick Start

```python
import azure.functions as func
import azure.functions.connector_triggers as ct

app = func.FunctionApp()

@ct.generic_connection_trigger(
    connection_id="%OFFICE365_CONNECTION_ID%",
    trigger_path="/Mail/OnNewEmail",
    trigger_queries={"folderPath": "Inbox"},
)
async def on_new_email(item: dict):
    print(f"New email: {item['subject']}")

ct.register_connector_triggers(app)
```

## Installation

```bash
# From git
pip install azure-functions-connector-triggers@git+https://github.com/anthonychu/azure-functions-connector-triggers-python.git

# For local development
pip install -e .
```

## Prerequisites

1. **Azure API Connection** — Create and authenticate a managed connector connection (e.g., Office 365) in your Azure subscription
2. **RBAC** — Grant your Function App's managed identity access to the connection:

   Create a custom role:
   ```json
   {
     "Name": "API Connection Invoker",
     "Actions": [
       "Microsoft.Web/connections/dynamicInvoke/action",
       "Microsoft.Web/connections/read"
     ]
   }
   ```

   Or assign **Logic App Contributor** scoped to the connection resource.

3. **App Settings** — Set `OFFICE365_CONNECTION_ID` (or equivalent) to the full ARM resource ID of your connection:
   ```
   /subscriptions/{subId}/resourceGroups/{rg}/providers/Microsoft.Web/connections/{name}
   ```

## How It Works

1. A **timer function** fires every minute (configurable) and polls each registered connector trigger
2. New items are enqueued to an **Azure Storage Queue**
3. A **queue-triggered function** calls your handler for each item, scaling out automatically

State (cursor, backoff) is persisted in **blob storage** so polling resumes across restarts.

## Configuration

### Decorator Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `connection_id` | str | required | ARM resource ID of the API connection. Supports `%VAR%` / `$VAR` env var syntax. |
| `trigger_path` | str | required | Connector trigger path (e.g., `/Mail/OnNewEmail`) |
| `trigger_queries` | dict | `{}` | Query parameters for the trigger. Values support env var syntax. |
| `min_interval` | int | `60` | Minimum polling interval in seconds (after items found) |
| `max_interval` | int | `300` | Maximum polling interval in seconds (backoff cap) |

### Registration

```python
ct.register_connector_triggers(app, poll_interval="0 */1 * * * *")
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `poll_interval` | str | `"0 */1 * * * *"` | CRON schedule for the polling timer |

## Common Trigger Paths

| Connector | Trigger | Path |
|-----------|---------|------|
| Office 365 | New email | `/Mail/OnNewEmail` |
| Office 365 | New calendar event | `/datasets/calendars/v3/tables/{calendarId}/onnewitems` |
| Salesforce | Record created | `/datasets/default/tables/{object}/onnewitems` |
| Salesforce | Record modified | `/datasets/default/tables/{object}/onupdateditems` |
| SharePoint | New list item | `/datasets/{siteUrl}/tables/{listId}/onnewitems` |

## Samples

See the [samples/](samples/) directory for complete working examples.

## License

MIT
