# azure-functions-connectors

> ⚠️ **Experimental** — This project is a prototype and not ready for production use. APIs may change without notice.

Connector bindings for Azure Functions (Python). Poll Azure managed connectors for new data and call connector actions using a simple decorator and client API.

## Features

- **Typed connector support** — Office 365, SharePoint, Salesforce, Teams, Google Calendar (triggers + client), Gmail (client)
- **Generic connector support** — `generic_trigger()` and `ConnectorClient` work with Azure managed connectors beyond the typed helpers
- **Clients** — send emails, create events, manage contacts, query CRM records, and call connector actions
- **Strongly-typed** — `Office365Email`, `GoogleCalendarEvent`, `TeamsMessage` models with snake_case properties + dict access
- **Automatic scale-out** — items dispatched via Storage Queue for parallel processing
- **Cursor-based polling** — only new items returned, no duplicates
- **Exponential backoff** — fast when active, quiet when idle

## Supported Connectors

- **Office 365 Outlook** — typed polling triggers and typed client
- **SharePoint Online** — typed polling triggers and typed client
- **Salesforce** — typed polling triggers and typed client
- **Microsoft Teams** — typed triggers (action-based) and typed client
- **Google Calendar** — typed triggers (action-based) and typed client
- **Gmail** — typed client (no triggers available)
- **Generic Azure managed connectors** — use `connectors.generic_trigger(...)` and `connectors.get_client(...)`

## Quick Start

```python
import azure.functions as func
import azure.functions_connectors as fc
from azure.functions_connectors import Office365Email

app = func.FunctionApp()
connectors = fc.FunctionsConnectors(app)

# Strongly-typed trigger with typed item model
@connectors.office365.new_email_trigger(
    connection_id="%OFFICE365_CONNECTION_ID%",
    folder="Inbox",
)
async def on_new_email(email: Office365Email):
    print(f"New email from {email.sender}: {email.subject}")
    print(f"Preview: {email.body_preview}")

# Generic trigger — works with any managed connector
@connectors.generic_trigger(
    connection_id="%SALESFORCE_CONNECTION_ID%",
    trigger_path="/trigger/datasets/default/tables/Lead/onnewitems",
)
async def on_new_lead(item: dict):
    print(f"New lead: {item['Name']}")

# Typed Office 365 client for calling actions
o365 = connectors.office365.get_client(connection_id="%OFFICE365_CONNECTION_ID%")

async def example_actions():
    await o365.send_email(to="user@company.com", subject="Hi", body="Hello!")
    emails = await o365.get_emails(folder="Inbox", top=5)
    event = await o365.create_event(subject="Meeting", start="...", end="...", timezone="...")

# Typed Teams trigger + typed model
@connectors.teams.new_channel_message_trigger(
    connection_id="%TEAMS_CONNECTION_ID%",
    team_id="%TEAMS_TEAM_ID%",
    channel_id="%TEAMS_CHANNEL_ID%",
)
async def on_channel_message(message: fc.TeamsMessage):
    print(f"New channel message: {message.body_preview}")

# Generic client for any connector
client = connectors.get_client(connection_id="%SALESFORCE_CONNECTION_ID%")

async def example_generic():
    result = await client.invoke("GET", "/datasets/default/tables/Lead/items")

# Typed Teams client for calling actions
teams = connectors.teams.get_client(connection_id="%TEAMS_CONNECTION_ID%")

async def example_teams():
    channels = await teams.list_channels("%TEAMS_TEAM_ID%")
```

## Installation

```bash
# Download and install the .whl from the latest GitHub release
pip install https://github.com/anthonychu/azure-functions-connectors-python/releases/download/v0.1.0b1/azure_functions_connectors-0.1.0b1-py3-none-any.whl
```

> **Tip:** Check the [Releases page](https://github.com/anthonychu/azure-functions-connectors-python/releases) for the latest version.

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

The SDK uses **cursor-based polling** to detect new items from connectors:

1. Each trigger is polled on a schedule. On the first poll, the SDK establishes a **cursor** that marks the current point in time.
2. On subsequent polls, only items created after the cursor are returned. The cursor advances automatically.
3. When new items are found, they're dispatched to your handler function. Processing scales out automatically.
4. When no new items are found, the SDK uses **exponential backoff** — starting at `min_interval` and doubling up to `max_interval`. This keeps polling fast when data is flowing and quiet when idle.
5. When items are found, the interval resets back to `min_interval`.

Polling state (cursor, interval) is persisted so triggers resume across restarts and deployments.

### Polling intervals

| Parameter | Default | Description |
|-----------|---------|-------------|
| `min_interval` | `60` seconds | Polling interval after items are found (fastest rate) |
| `max_interval` | `300` seconds | Maximum polling interval when idle (backoff cap) |

These can be configured on `generic_trigger()`:

```python
@connectors.generic_trigger(
    connection_id="%CONNECTION_ID%",
    trigger_path="/trigger/path",
    min_interval=30,   # poll every 30s after finding items
    max_interval=120,  # cap idle polling at 2 minutes
)
async def on_item(item: dict):
    ...
```

Typed triggers (e.g., `office365.new_email_trigger()`) use the defaults (60s / 300s).

## Configuration

### Decorator Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `connection_id` | str | required | ARM resource ID of the API connection. Supports `%VAR%` / `$VAR` env var syntax. |
| `trigger_path` | str | required | Connector trigger path (e.g., `/v3/Mail/OnNewEmail`) |
| `trigger_queries` | dict | `{}` | Query parameters for the trigger. Values support env var syntax. |
| `min_interval` | int | `60` | Polling interval in seconds after items are found |
| `max_interval` | int | `300` | Maximum polling interval in seconds (backoff cap) |

### Registration

No explicit registration call needed — `FunctionsConnectors(app)` handles everything.

## Common Trigger Paths

| Connector | Trigger | Path |
|-----------|---------|------|
| Office 365 | New email | `/v3/Mail/OnNewEmail` |
| Office 365 | New calendar event | `/datasets/calendars/v3/tables/{calendarId}/onnewitems` |
| Salesforce | Record created | `/trigger/datasets/default/tables/{object}/onnewitems` |
| Salesforce | Record modified | `/trigger/datasets/default/tables/{object}/onupdateditems` |
| SharePoint | New list item | `/datasets/{doubleEncodedSiteUrl}/tables/{listId}/onnewitems` |

`connectors.sharepoint.*` handles SharePoint's required site URL encoding automatically.

## Known Limitations

- **Teams triggers** support top-level channel posts and @mentions. Replies within threads and chat message triggers are not currently available.
- **Gmail** has no triggers and no list emails action — client supports send, reply, get, trash, and delete only.
- **Google Calendar triggers** detect new/updated events but rely on action-based polling (the connector's native triggers are webhook-only).
- **`http_request()` actions** on Office 365, Teams, and SharePoint connectors are not currently supported. Use the typed client methods or the Microsoft Graph SDK instead.
- **SharePoint generic paths** require special site URL encoding; the typed `connectors.sharepoint.*` helpers handle this automatically.

## Documentation

- **[Office 365 Connector](docs/office365.md)** — 7 triggers, 31 client methods, typed models (`Office365Email`, `Office365Event`)
- **[Microsoft Teams Connector](docs/teams.md)** — typed triggers, typed client, typed models
- **[SharePoint Connector](docs/sharepoint.md)** — 4 triggers, typed models, client helpers
- **[Salesforce Connector](docs/salesforce.md)** — 3 triggers, typed models, client helpers
- **[Google Calendar Connector](docs/google-calendar.md)** — 2 triggers, typed client, typed models (`GoogleCalendarEvent`)
- **[Gmail Connector](docs/gmail.md)** — typed client, typed models (`GmailEmail`)
- **[Generic APIs](docs/generic.md)** — `generic_trigger()`, `ConnectorClient`, `ConnectorItem`, architecture, RBAC
- **[Setup & Production Guide](docs/setup.md)** — Creating connections, authentication, RBAC, local dev, deployment

## Samples

- [samples/office365/](samples/office365/) — Office 365 triggers + typed client
- [samples/sharepoint/](samples/sharepoint/) — SharePoint triggers + typed client
- [samples/salesforce/](samples/salesforce/) — Salesforce triggers + typed client
- [samples/teams/](samples/teams/) — Teams triggers + typed client
- [samples/google-calendar/](samples/google-calendar/) — Google Calendar triggers + typed client
- [samples/gmail/](samples/gmail/) — Gmail typed client

## License

MIT
