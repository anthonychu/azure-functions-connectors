# Sample: Gmail Client (Actions Only)

This sample demonstrates Gmail **client-only** usage. Gmail does not support polling triggers in this SDK because the connector does not provide a list/poll action.

## Prerequisites

- Python 3.10+
- Azure Functions Core Tools v4
- An Azure API Connection for Gmail (authenticated via OAuth)
- A managed identity or service principal with `Microsoft.Web/connections/dynamicInvoke/action` on the connection

## Setup

1. Copy `local.settings.json.template` to `local.settings.json`
2. Fill in your Gmail connection resource ID
3. Install dependencies: `pip install -r requirements.txt`
4. Run: `func start`

## Included function

- `gmail_send_sample`: timer-triggered function that sends a test email with `GmailClient.send_email(...)`

The sample also includes commented usage for `get_email(...)` and `reply_to(...)`.
