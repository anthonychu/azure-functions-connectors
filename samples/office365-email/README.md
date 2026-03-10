# Sample: Office 365 Email Trigger

This sample demonstrates using `azure-functions-connectors` to process new emails from Office 365.

## Prerequisites

- Python 3.9+
- Azure Functions Core Tools v4
- An Azure API Connection for Office 365 (authenticated via OAuth)
- A managed identity or service principal with `Microsoft.Web/connections/dynamicInvoke/action` on the connection

## Setup

1. Copy `local.settings.json.template` to `local.settings.json`
2. Fill in your connection resource ID
3. Install dependencies: `pip install -r requirements.txt`
4. Run: `func start`

## How It Works

The `@generic_connection_trigger` decorator registers a polling trigger for new emails.
Behind the scenes, a timer function polls the Office 365 connector every minute and
enqueues new emails to a Storage Queue. A queue-triggered function then calls your
handler for each email.
