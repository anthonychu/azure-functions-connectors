# Google Calendar Connector API Documentation

## Table of Contents

- [Overview](#overview)
- [Finding Your IDs](#finding-your-ids)
- [Triggers](#triggers)
  - [new_event_trigger](#new_event_trigger)
  - [updated_event_trigger](#updated_event_trigger)
  - [Polling intervals](#polling-intervals)
- [Models](#models)
  - [GoogleCalendarEvent](#googlecalendarevent)
- [Client](#client)
  - [Calendar methods](#calendar-methods)
- [Known Limitations](#known-limitations)

## Overview

The Google Calendar connector provides:

- Action-based polling triggers for new and updated events:
  - `new_event_trigger(...)`
  - `updated_event_trigger(...)`
- A typed action client (`GoogleCalendarClient`) for calendar and event operations.
- A typed event model (`GoogleCalendarEvent`).

```python
client = connectors.googlecalendar.get_client("%GOOGLE_CALENDAR_CONNECTION_ID%")
```

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

Store it as an app setting (e.g., `GOOGLE_CALENDAR_CONNECTION_ID`) and reference it with `%GOOGLE_CALENDAR_CONNECTION_ID%` in your trigger decorators.

### Calendar ID

The `calendar_id` is typically your email address (e.g., `user@gmail.com`) or `primary` for your default calendar.

Use the client to discover calendar IDs:

```python
client = connectors.google_calendar.get_client("%GOOGLE_CALENDAR_CONNECTION_ID%")
calendars = await client.list_calendars()
for cal in calendars.get("items", []):
    print(f"{cal.get('summary')}: {cal.get('id')}")
```


## Triggers

Google Calendar trigger decorators are available on `connectors.googlecalendar`.

### `new_event_trigger(connection_id: str, calendar_id: str, min_interval: int = 60, max_interval: int = 300) -> Callable`

Fires when new events are created in the target calendar.

```python
from azure.functions_connectors._triggers.googlecalendar import GoogleCalendarEvent

@connectors.googlecalendar.new_event_trigger(
    connection_id="%GOOGLE_CALENDAR_CONNECTION_ID%",
    calendar_id="%GOOGLE_CALENDAR_ID%",
)
async def on_new_event(event: GoogleCalendarEvent):
    print(event.id, event.summary)
```

### `updated_event_trigger(connection_id: str, calendar_id: str, min_interval: int = 60, max_interval: int = 300) -> Callable`

Fires when existing events are updated in the target calendar.

```python
@connectors.googlecalendar.updated_event_trigger(
    connection_id="%GOOGLE_CALENDAR_CONNECTION_ID%",
    calendar_id="%GOOGLE_CALENDAR_ID%",
)
async def on_updated_event(event: GoogleCalendarEvent):
    print(event.id, event.updated_at)
```

> **Note:** Native Google Calendar triggers are webhook-only and do not work through dynamicInvoke. These SDK triggers use action-based polling for reliable behavior.

### Polling intervals

Both trigger methods accept:

- `min_interval` (default: `60`) — minimum seconds between polls.
- `max_interval` (default: `300`) — maximum backoff interval when idle.

## Models

### `GoogleCalendarEvent`

Typed wrapper for Google Calendar event payloads.

| Property | Type | Description |
|----------|------|-------------|
| `id` | `str` | Event ID (`id`). |
| `summary` | `str` | Event summary (`summary`). |
| `description` | `str` | Event description (`description`). |
| `location` | `str` | Event location (`location`). |
| `start` | `dict \| str` | Event start (`start`). |
| `end` | `dict \| str` | Event end (`end`). |
| `status` | `str` | Event status (`status`). |
| `creator` | `str` | Creator email (`creator.email`). |
| `organizer` | `str` | Organizer email (`organizer.email`). |
| `attendees` | `list` | Event attendees (`attendees`). |
| `html_link` | `str` | Browser URL (`htmlLink`). |
| `created_at` | `str` | Creation timestamp (`created`). |
| `updated_at` | `str` | Last update timestamp (`updated`). |

## Client

Create the typed client:

```python
client = connectors.googlecalendar.get_client("%GOOGLE_CALENDAR_CONNECTION_ID%")
```

### Calendar methods

#### `list_calendars()`
```python
calendars = await client.list_calendars()
```

#### `list_events(calendar_id: str, time_min: str | None = None, time_max: str | None = None, q: str | None = None, updated_min: str | None = None, max_results: int | None = None)`
```python
events = await client.list_events(
    calendar_id="primary",
    time_min="2026-03-12T00:00:00Z",
    time_max="2026-03-19T00:00:00Z",
    max_results=25,
)
```

#### `get_event(calendar_id: str, event_id: str)`
```python
event = await client.get_event("primary", "<event-id>")
```

#### `create_event(calendar_id: str, summary: str, start: str, end: str, description: str | None = None, location: str | None = None, attendees: list[dict] | None = None)`
```python
created = await client.create_event(
    calendar_id="primary",
    summary="Weekly sync",
    start="2026-03-12T17:00:00Z",
    end="2026-03-12T17:30:00Z",
    description="Project status",
)
```

#### `update_event(calendar_id: str, event_id: str, **fields)`
```python
updated = await client.update_event(
    "primary",
    "<event-id>",
    summary="Updated title",
)
```

#### `delete_event(calendar_id: str, event_id: str)`
```python
await client.delete_event("primary", "<event-id>")
```

## Known Limitations

- Triggering is action-based polling, not native webhook trigger registration.
- Polling cursor is timestamp-based and optimized for incremental sync (`updatedMin` for updated-event trigger).
- List-event trigger ordering relies on Google Calendar `orderBy=startTime` with `singleEvents=true`.
