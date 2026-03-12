# Gmail Connector API Documentation

## Table of Contents

- [Overview](#overview)
- [Finding Your IDs](#finding-your-ids)
- [Triggers](#triggers)
- [Models](#models)
  - [GmailEmail](#gmailemail)
- [Client](#client)
  - [Email](#email)
- [Known Limitations](#known-limitations)

## Overview

The Gmail connector currently provides:

- A typed **action client** (`GmailClient`) for Gmail email operations.
- A typed helper model:
  - `GmailEmail`
- A `connectors.gmail.get_client(...)` helper for creating the typed client from `FunctionsConnectors`.

```python
gmail = connectors.gmail.get_client(connection_id="%GMAIL_CONNECTION_ID%")
```

Gmail is **client only** in this SDK. No polling trigger decorators are available.

## Finding Your IDs

### Connection ID

The `connection_id` is the full ARM resource ID of your API Connection in Azure:

```
/subscriptions/{subscription-id}/resourceGroups/{resource-group}/providers/Microsoft.Web/connections/{connection-name}
```

To find it:
1. Open the [Azure Portal](https://portal.azure.com)
2. Navigate to your resource group
3. Find your API Connection resource
4. The resource ID is in the **Properties** blade, or construct it from your subscription ID, resource group name, and connection name

Alternatively, use the CLI:
```bash
az resource list --resource-group {rg} --resource-type Microsoft.Web/connections --query "[].id" -o tsv
```

Store it as an app setting (e.g., `GMAIL_CONNECTION_ID`) and reference it with `%GMAIL_CONNECTION_ID%` in your decorators.


## Triggers

Gmail does not expose trigger decorators in this SDK.

> **Polling interval note:** `min_interval` and `max_interval` apply only to polling triggers. Gmail has no trigger support, so these parameters are **not applicable**.

## Models

### `GmailEmail`

Typed wrapper for Gmail email payloads.

| Property | Type | Description |
|----------|------|-------------|
| `id` | `str` | Message ID (`Id` or `id`). |
| `subject` | `str` | Email subject (`Subject` or `subject`). |
| `body` | `str` | Email body (`Body` or `body`). |
| `from_address` | `str` | Sender (`From` or `from`). |
| `to` | `str \| list \| dict` | Recipient field (`To` or `to`). |
| `cc` | `str \| list \| dict \| None` | Carbon-copy field (`Cc` or `cc`). |
| `bcc` | `str \| list \| dict \| None` | Blind-carbon-copy field (`Bcc` or `bcc`). |
| `date_time_received` | `str` | Receive time (`DateTimeReceived` or `dateTimeReceived`). |
| `is_read` | `bool` | Read state (`IsRead` or `isRead`). |
| `has_attachment` | `bool` | Attachment flag (`HasAttachment` or `hasAttachment`). |
| `importance` | `str` | Importance value (`Importance` or `importance`). |

## Client

Create the typed client:

```python
client = connectors.gmail.get_client("%GMAIL_CONNECTION_ID%")
```

### Email

#### `send_email(to: str, subject: str, body: str, cc: str | None = None, bcc: str | None = None, importance: str = "Normal")`

```python
await client.send_email(
    to="user@contoso.com",
    subject="Hello",
    body="Sent from Gmail connector",
    cc="copy@contoso.com",
)
```

#### `reply_to(message_id: str, body: str | None = None, to: str | None = None, cc: str | None = None, bcc: str | None = None, reply_all: bool = False)`

```python
await client.reply_to(
    message_id="<message-id>",
    body="Thanks!",
    reply_all=False,
)
```

#### `get_email(message_id: str, include_attachments: bool = False)`

```python
message = await client.get_email("<message-id>", include_attachments=True)
```

#### `trash_email(message_id: str)`

```python
await client.trash_email("<message-id>")
```

#### `delete_email(message_id: str)`

```python
await client.delete_email("<message-id>")
```

## Known Limitations

- **No list emails action:** the Gmail connector does not provide a list/poll endpoint.
- **No triggers:** since polling is not available, trigger decorators are not supported for Gmail in this SDK.
