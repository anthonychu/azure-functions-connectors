# Sample: Office 365 Triggers & Client

This sample demonstrates Office 365 triggers (new email, flagged email, calendar events) plus a timer-driven typed client example.

## Prerequisites

- Python 3.10+
- Azure Functions Core Tools v4
- An Azure API Connection for Office 365 (authenticated via OAuth)
- A managed identity or service principal with `Microsoft.Web/connections/dynamicInvoke/action` on the connection

## Setup

1. Copy `local.settings.json.template` to `local.settings.json`
2. Fill in your connection resource ID
3. Install dependencies: `pip install -r requirements.txt`
4. Run: `func start`

## How It Works

- `connectors.office365.*_trigger(...)` registers polling triggers for emails and calendar events.
- The SDK adds an internal timer that polls the Office 365 connector and enqueues new items to Storage Queue.
- Queue-triggered functions dispatch typed `Office365Email` / `Office365Event` payloads to your handlers.
- A separate sample timer function shows how to use the typed `Office365Client` for read-only actions like `get_emails()` and `get_calendars()`.
