# Generic Connector APIs

## Table of Contents

- [Overview](#overview)
- [FunctionsConnectors](#functionsconnectors)
- [Typed Connector Helpers](#typed-connector-helpers)
- [Generic Trigger](#generic-trigger)
  - [Signature](#signature)
  - [Parameters](#parameters)
  - [How it works](#how-it-works)
  - [Examples](#example-salesforce--sharepoint)
  - [Type hints](#type-hints-for-handler-item)
- [Generic Client](#generic-client)
  - [ConnectorClient](#constructor-1)
  - [invoke()](#invoke)
  - [ConnectorError](#connectorerror)
  - [Examples](#examples)
- [ConnectorItem Base Class](#connectoritem-base-class)
  - [Subclassing pattern](#subclassing-pattern)
- [Architecture](#architecture)
- [RBAC](#rbac)
- [Connector-specific Notes](#connector-specific-notes)

## Overview

The generic APIs are connector-agnostic and work with **any Azure managed connector** (Office 365, Salesforce, SharePoint, Dynamics, and 500+ others).  
Use them when you want one consistent trigger/client pattern across different connector types.

---

## FunctionsConnectors

`FunctionsConnectors` is the main entry point for registering triggers and creating connector clients.

### Constructor

```python
FunctionsConnectors(app: func.FunctionApp)
```

| Parameter | Type | Required | Description |
|---|---|---|---|
| `app` | `azure.functions.FunctionApp` | Yes | Function App used to register timer + queue trigger functions. |

### `get_client(connection_id)`

```python
get_client(connection_id: str) -> ConnectorClient
```

Returns a generic `ConnectorClient` for invoking any connector action.

### `office365` property

`connectors.office365` exposes Office 365-specific typed triggers and typed client helpers.  
Use generic APIs when you need connector-agnostic behavior; use `office365` when you want typed Office 365 convenience methods.

## Typed Connector Helpers

`FunctionsConnectors` also exposes connector-specific helper properties:

- `connectors.office365` — typed triggers + typed client
- `connectors.salesforce` — typed triggers + typed client
- `connectors.sharepoint` — typed triggers + typed client, with SharePoint site URL encoding handled for you
- `connectors.teams` — typed triggers + typed client

---

## Generic Trigger

### Signature

```python
connectors.generic_trigger(
    connection_id: str,
    trigger_path: str,
    trigger_queries: dict[str, str] | None = None,
    min_interval: int = 60,
    max_interval: int = 300,
) -> Callable
```

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `connection_id` | `str` | required | ARM resource ID of the API connection. Supports env var resolution (`%VAR%`, `$VAR`). |
| `trigger_path` | `str` | required | Connector trigger path (for example `/trigger/datasets/default/tables/Lead/onnewitems`). |
| `trigger_queries` | `dict[str, str] \| None` | `None` | Query parameters sent with the trigger request. |
| `min_interval` | `int` | `60` | Polling interval (seconds) after items are found. Must be `>= 1`. |
| `max_interval` | `int` | `300` | Maximum polling interval (seconds) when idle. Must be `>= min_interval`. |

### How polling works

Triggers use **cursor-based polling** with **exponential backoff**:

1. On the first poll, a cursor is established marking the current point in time. No items are returned.
2. On subsequent polls, the connector returns only items created since the cursor.
3. When items are found, the polling interval resets to `min_interval` (default: 60 seconds).
4. When no items are found, the interval doubles each cycle up to `max_interval` (default: 300 seconds).
5. If your handler parameter is a `ConnectorItem` subclass, items are auto-wrapped into that model.

Example with custom intervals:

```python
@connectors.generic_trigger(
    connection_id="%CONNECTION_ID%",
    trigger_path="/trigger/datasets/default/tables/Lead/onnewitems",
    min_interval=30,   # poll every 30s when active
    max_interval=120,  # cap at 2 minutes when idle
)
async def on_new_lead(item: dict):
    print(item["Name"])
```

### Example: Salesforce + SharePoint

```python
import azure.functions as func
import azure.functions_connectors as fc
from azure.functions_connectors import ConnectorItem

app = func.FunctionApp()
connectors = fc.FunctionsConnectors(app)

@connectors.generic_trigger(
    connection_id="%SALESFORCE_CONNECTION_ID%",
    trigger_path="/trigger/datasets/default/tables/Lead/onnewitems",
    trigger_queries={"$select": "Id,Name,Company,Email"},
)
async def on_new_lead(item: dict):
    print("Lead:", item.get("Name"), item.get("Email"))

class SharePointListItem(ConnectorItem):
    @property
    def id(self) -> str:
        return self.get("ID", "")

    @property
    def title(self) -> str:
        return self.get("Title", "")

@connectors.generic_trigger(
    connection_id="%SHAREPOINT_CONNECTION_ID%",
    trigger_path="/datasets/https%253A%252F%252Fcontoso.sharepoint.com%252Fsites%252FEngineering/tables/%SHAREPOINT_LIST_ID%/onnewitems",
)
async def on_new_sp_item(item: SharePointListItem):
    print("New SharePoint item:", item.id, item.title)
```

> For SharePoint, generic trigger/client paths require specially encoded site URLs. Use `connectors.sharepoint.*` instead to avoid manual encoding.

### Type hints for handler item

- `item: dict` → raw payload access (maximum flexibility).
- `item: MyTypedModel` where `MyTypedModel(ConnectorItem)` → typed properties + dict fallback.

---

## Generic Client

### Constructor

```python
ConnectorClient(connection_id: str)
```

Creates a connector client bound to one API connection resource ID.

### `invoke(...)`

```python
await client.invoke(
    method: str,
    path: str,
    queries: dict[str, str] | None = None,
    body: dict | None = None,
) -> dict
```

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `method` | `str` | required | Logical connector operation method (`GET`, `POST`, `PATCH`, `DELETE`, etc.). |
| `path` | `str` | required | Connector operation path (for example `/v2/Mail`, `/datasets/default/tables/Lead/items`). |
| `queries` | `dict[str, str] \| None` | `None` | Query string parameters passed to the connector operation. |
| `body` | `dict \| None` | `None` | Request payload sent to the connector operation. |

### Returns

- Returns the connector response body as `dict`.
- Raises `ConnectorError` for transport failures or non-success connector responses.

### `ConnectorError`

```python
class ConnectorError(Exception):
    status: str | int
    body: str
```

- `status`: HTTP/connector status code or status label.
- `body`: raw response body text when available.

### Examples

```python
client = connectors.get_client("%SALESFORCE_CONNECTION_ID%")

# Salesforce: list leads
leads = await client.invoke(
    "GET",
    "/datasets/default/tables/Lead/items",
    queries={"$top": "10"},
)

# SharePoint: create list item
created = await client.invoke(
    "POST",
    "/datasets/{siteUrl}/tables/{listId}/items",
    body={"Title": "New item from Function"},
)

# Dynamics 365: invoke action/operation path
result = await client.invoke(
    "POST",
    "/datasets/default/tables/accounts/items",
    body={"name": "Contoso Ltd"},
)
```

---

## `ConnectorItem` Base Class

`ConnectorItem` wraps the raw connector payload and is designed as a base class for your typed models.

### Subclassing pattern

```python
from azure.functions_connectors import ConnectorItem

class SalesforceLead(ConnectorItem):
    @property
    def id(self) -> str:
        return self.get("Id", "")

    @property
    def name(self) -> str:
        return self.get("Name", "")

    @property
    def company(self) -> str:
        return self.get("Company", "")
```

### Dict-style access

`ConnectorItem` supports both typed properties and raw dict access:

- `item["Key"]` (`__getitem__`)
- `item.get("Key", default)`
- `item.keys()`
- `item.items()`
- `item.to_dict()`

### Example usage

```python
@connectors.generic_trigger(
    connection_id="%SALESFORCE_CONNECTION_ID%",
    trigger_path="/datasets/default/tables/Lead/onnewitems",
)
async def on_lead(lead: SalesforceLead):
    print(lead.name)
    print(lead["Email"])           # raw access
    print(list(lead.keys()))       # dict keys
```

---

## Architecture

The SDK uses a **timer + storage** pattern internally:

1. A timer polls each registered connector trigger on a schedule.
2. Cursor and polling state are persisted, so polling resumes safely across restarts and deployments.
3. New items are dispatched to your handler functions for scalable parallel processing.

---

## RBAC

Your Function App identity needs permission to invoke API connections:

```json
{
  "Name": "API Connection Invoker",
  "Actions": [
    "Microsoft.Web/connections/dynamicInvoke/action",
    "Microsoft.Web/connections/read"
  ]
}
```

Scope this role to the target connection resource(s) or resource group.

## Connector-specific Notes

- **Teams:** triggers support top-level channel posts and @mentions. Replies within threads and chat message triggers are not currently available.
- **SharePoint:** the typed helpers handle site URL encoding automatically. If using generic APIs, you must encode the site URL yourself.
- **`http_request()` actions:** the raw HTTP request escape hatch on Office 365, Teams, and SharePoint connectors is not currently supported. Use the typed client methods or the native SDK (e.g., Microsoft Graph SDK) instead.
