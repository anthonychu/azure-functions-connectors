# Office 365 Connector API Documentation

## Table of Contents

- [Overview](#overview)
- [Triggers](#triggers)
  - [new_email_trigger](#new_email_trigger)
  - [mention_email_trigger](#mention_email_trigger)
  - [shared_mailbox_email_trigger](#shared_mailbox_email_trigger)
  - [flagged_email_trigger](#flagged_email_trigger)
  - [new_event_trigger](#new_event_trigger)
  - [upcoming_event_trigger](#upcoming_event_trigger)
  - [event_changed_trigger](#event_changed_trigger)
- [Typed Models](#typed-models)
  - [Office365Email](#office365email)
  - [Office365Event](#office365event)
- [Client](#client)
  - [Email Actions](#email-actions) — send, get, reply, forward, move, flag, delete, draft, attachments
  - [Calendar Actions](#calendar-actions) — get, create, update, delete, calendar view, rooms, meetings
  - [Contact Actions](#contact-actions) — get, create, update, delete
  - [Utility](#utility) — raw HTTP request, get calendars
- [Known Limitations](#known-limitations)

## Overview

The Office 365 connector provides:

- **Trigger decorators** (via `Office365Triggers`) for polling email and calendar events.
- A typed **action client** (`Office365Client`) for email, calendar, contact, and utility operations.
- Typed trigger item wrappers:
  - `Office365Email` for mail triggers
  - `Office365Event` for calendar triggers

Get a client from triggers:

```python
o365 = connectors.office365.get_client(connection_id="office365-conn")
```

> **Limitation:** `Office365Client.http_request()` is currently not usable through this SDK because the underlying connector models `Method` and `Uri` as headers, and ARM `dynamicInvoke` does not forward them correctly. Prefer the typed client methods or the Microsoft Graph SDK for unsupported endpoints.

---

## Triggers

> Trigger decorators are created from `connectors.office365`.
> Handler payloads can be wrapped as `Office365Email` or `Office365Event` depending on trigger type.

### `new_email_trigger(connection_id: str, folder: str = "Inbox", from_filter: str | None = None, to_filter: str | None = None, cc_filter: str | None = None, importance: str | None = None, subject_filter: str | None = None, include_attachments: bool = False, only_with_attachments: bool = False) -> Callable`

Fires when a **new email arrives** in the selected folder.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `connection_id` | `str` | — | Connector connection ID. |
| `folder` | `str` | `"Inbox"` | Mail folder path to watch. |
| `from_filter` | `str \| None` | `None` | Sender filter. |
| `to_filter` | `str \| None` | `None` | Recipient filter. |
| `cc_filter` | `str \| None` | `None` | CC recipient filter. |
| `importance` | `str \| None` | `None` | Importance filter (for example `High`, `Normal`, `Low`). |
| `subject_filter` | `str \| None` | `None` | Subject substring filter. |
| `include_attachments` | `bool` | `False` | Include attachment content metadata in payload. |
| `only_with_attachments` | `bool` | `False` | Only fire for messages with attachments. |

**Returns:** Trigger decorator (`Callable`).

**Example:**
```python
@connectors.office365.new_email_trigger(
    connection_id="office365-conn",
    folder="Inbox",
    subject_filter="[Action Required]",
)
async def on_email(item: dict):
    email = Office365Email(item)  # typed model for this trigger
    print(email.subject)
```

**Typed model:** `Office365Email`

### `mention_email_trigger(connection_id: str, folder: str = "Inbox", from_filter: str | None = None, to_filter: str | None = None, cc_filter: str | None = None, importance: str | None = None, subject_filter: str | None = None, include_attachments: bool = False, only_with_attachments: bool = False) -> Callable`

Fires when a **new “mention me” email** arrives.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `connection_id` | `str` | — | Connector connection ID. |
| `folder` | `str` | `"Inbox"` | Mail folder path to watch. |
| `from_filter` | `str \| None` | `None` | Sender filter. |
| `to_filter` | `str \| None` | `None` | Recipient filter. |
| `cc_filter` | `str \| None` | `None` | CC recipient filter. |
| `importance` | `str \| None` | `None` | Importance filter. |
| `subject_filter` | `str \| None` | `None` | Subject substring filter. |
| `include_attachments` | `bool` | `False` | Include attachment metadata/content when available. |
| `only_with_attachments` | `bool` | `False` | Only fire for messages with attachments. |

**Returns:** Trigger decorator (`Callable`).

**Example:**
```python
@connectors.office365.mention_email_trigger(
    connection_id="office365-conn",
    folder="Inbox",
)
async def on_mention(item: dict):
    email = Office365Email(item)
    print(email.sender, email.subject)
```

**Typed model:** `Office365Email`

### `shared_mailbox_email_trigger(connection_id: str, mailbox_address: str, folder: str = "Inbox", from_filter: str | None = None, to_filter: str | None = None, cc_filter: str | None = None, importance: str | None = None, subject_filter: str | None = None, include_attachments: bool = False) -> Callable`

Fires when a **new email arrives in a shared mailbox**.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `connection_id` | `str` | — | Connector connection ID. |
| `mailbox_address` | `str` | — | Shared mailbox SMTP address. |
| `folder` | `str` | `"Inbox"` | Shared mailbox folder path to watch. |
| `from_filter` | `str \| None` | `None` | Sender filter. |
| `to_filter` | `str \| None` | `None` | Recipient filter. |
| `cc_filter` | `str \| None` | `None` | CC recipient filter. |
| `importance` | `str \| None` | `None` | Importance filter. |
| `subject_filter` | `str \| None` | `None` | Subject substring filter. |
| `include_attachments` | `bool` | `False` | Include attachments in trigger payload when available. |

**Returns:** Trigger decorator (`Callable`).

**Example:**
```python
@connectors.office365.shared_mailbox_email_trigger(
    connection_id="office365-conn",
    mailbox_address="support@contoso.com",
    folder="Inbox",
)
async def on_shared_mail(item: dict):
    email = Office365Email(item)
    print(email.to, email.subject)
```

**Typed model:** `Office365Email`

### `flagged_email_trigger(connection_id: str, folder: str = "Inbox", from_filter: str | None = None, to_filter: str | None = None, importance: str | None = None, subject_filter: str | None = None) -> Callable`

Fires when an email is **flagged**.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `connection_id` | `str` | — | Connector connection ID. |
| `folder` | `str` | `"Inbox"` | Folder path to watch. |
| `from_filter` | `str \| None` | `None` | Sender filter. |
| `to_filter` | `str \| None` | `None` | Recipient filter. |
| `importance` | `str \| None` | `None` | Importance filter. |
| `subject_filter` | `str \| None` | `None` | Subject substring filter. |

**Returns:** Trigger decorator (`Callable`).

**Example:**
```python
@connectors.office365.flagged_email_trigger(connection_id="office365-conn")
async def on_flagged(item: dict):
    email = Office365Email(item)
    print(email.id, email.subject)
```

**Typed model:** `Office365Email`

### `new_event_trigger(connection_id: str, calendar_id: str = "Calendar") -> Callable`

Fires when a **new calendar event is created**.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `connection_id` | `str` | — | Connector connection ID. |
| `calendar_id` | `str` | `"Calendar"` | Calendar table/id to monitor. |

**Returns:** Trigger decorator (`Callable`).

**Example:**
```python
@connectors.office365.new_event_trigger(
    connection_id="office365-conn",
    calendar_id="Calendar",
)
async def on_new_event(item: dict):
    event = Office365Event(item)
    print(event.subject, event.start)
```

**Typed model:** `Office365Event`

### `upcoming_event_trigger(connection_id: str, calendar_id: str = "Calendar", look_ahead_minutes: int | None = None) -> Callable`

Fires when an **upcoming event is about to start**.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `connection_id` | `str` | — | Connector connection ID. |
| `calendar_id` | `str` | `"Calendar"` | Calendar ID (`table` query value). |
| `look_ahead_minutes` | `int \| None` | `None` | Look-ahead window in minutes for upcoming event checks. |

**Returns:** Trigger decorator (`Callable`).

**Example:**
```python
@connectors.office365.upcoming_event_trigger(
    connection_id="office365-conn",
    look_ahead_minutes=15,
)
async def on_upcoming(item: dict):
    event = Office365Event(item)
    print(f"Starting soon: {event.subject}")
```

**Typed model:** `Office365Event`

### `event_changed_trigger(connection_id: str, calendar_id: str = "Calendar", incoming_days: int | None = None, past_days: int | None = None) -> Callable`

Fires when a calendar event is **added, updated, or deleted**.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `connection_id` | `str` | — | Connector connection ID. |
| `calendar_id` | `str` | `"Calendar"` | Calendar table/id to monitor. |
| `incoming_days` | `int \| None` | `None` | Include event changes this many days in the future. |
| `past_days` | `int \| None` | `None` | Include event changes this many days in the past. |

**Returns:** Trigger decorator (`Callable`).

**Example:**
```python
@connectors.office365.event_changed_trigger(
    connection_id="office365-conn",
    incoming_days=30,
    past_days=1,
)
async def on_event_change(item: dict):
    event = Office365Event(item)
    print(event.id, event.subject)
```

**Typed model:** `Office365Event`

---

## Typed Models

All typed trigger models inherit from `ConnectorItem` and support:

- typed property access (`email.subject`, `event.start`)
- dict-style access (`email["Subject"]`, `event.get("start")`)
- pass-through helpers: `get`, `keys`, `values`, `items`, `to_dict`

### `Office365Email`

Typed wrapper for Office 365 email payloads. Supports both camelCase and PascalCase source keys.

| Property | Type | Description |
|----------|------|-------------|
| `id` | `str` | Message ID (`id` / `Id`). |
| `subject` | `str` | Email subject (`subject` / `Subject`). |
| `sender` | `str` | Sender (`from` / `From`). |
| `to` | `str` | To recipients (`toRecipients` / `To`). |
| `cc` | `str \| None` | CC recipients (`ccRecipients` / `Cc`). |
| `bcc` | `str \| None` | BCC recipients (`bccRecipients` / `Bcc`). |
| `body` | `str` | Message body (`body` / `Body`). |
| `body_preview` | `str` | Body preview (`bodyPreview` / `BodyPreview`). |
| `importance` | `str` | Importance (`importance` / `Importance`). |
| `received_at` | `str` | Receive timestamp (`receivedDateTime` / `DateTimeReceived`). |
| `has_attachment` | `bool` | Whether message has attachments (`hasAttachments` / `HasAttachment`). |
| `is_read` | `bool` | Read state (`isRead` / `IsRead`). |
| `is_html` | `bool` | HTML body flag (`isHtml` / `IsHtml`). |
| `internet_message_id` | `str` | Internet message ID (`internetMessageId` / `InternetMessageId`). |
| `conversation_id` | `str` | Conversation/thread ID (`conversationId` / `ConversationId`). |
| `attachments` | `list` | Attachment list (`attachments` / `Attachments`). |
| `reply_to` | `str \| None` | Reply-to addresses (`replyTo` / `ReplyTo`). |

**Dict access example:**
```python
email = Office365Email(item)
subject = email.subject
raw_subject = email.get("Subject") or email.get("subject")
message_id = email["Id"] if "Id" in email else email["id"]
raw = email.to_dict()
```

### `Office365Event`

Typed wrapper for Office 365 calendar event payloads. Supports both camelCase and PascalCase source keys.

| Property | Type | Description |
|----------|------|-------------|
| `id` | `str` | Event ID (`id` / `Id`). |
| `subject` | `str` | Event subject (`subject` / `Subject`). |
| `body` | `str` | Event body (`body` / `Body`). |
| `body_preview` | `str` | Event body preview (`bodyPreview` / `BodyPreview`). |
| `start` | `str` | Start datetime (`start` / `Start`). |
| `end` | `str` | End datetime (`end` / `End`). |
| `location` | `str` | Event location (`location` / `Location`). |
| `organizer` | `str` | Organizer (`organizer` / `Organizer`). |
| `is_all_day` | `bool` | All-day flag (`isAllDay` / `IsAllDay`). |
| `show_as` | `str` | Availability status (`showAs` / `ShowAs`). |
| `attendees` | `list` | Attendee list (`attendees` / `Attendees`). |
| `is_reminder_on` | `bool` | Reminder enabled (`isReminderOn` / `IsReminderOn`). |
| `recurrence` | `str \| None` | Recurrence definition (`recurrence` / `Recurrence`). |

**Dict access example:**
```python
event = Office365Event(item)
start = event.start
raw_start = event.get("Start") or event.get("start")
event_id = event["Id"] if "Id" in event else event["id"]
raw = event.to_dict()
```

---

## Client

Create the typed client from triggers:

```python
o365 = connectors.office365.get_client(connection_id="office365-conn")
```

### Email Actions

### `send_email(to: str, subject: str, body: str, cc: str | None = None, bcc: str | None = None, importance: str = "Normal")`

Send an email.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `to` | `str` | — | Recipient list (typically `;`-separated). |
| `subject` | `str` | — | Email subject. |
| `body` | `str` | — | Email body content. |
| `cc` | `str \| None` | `None` | CC recipients. |
| `bcc` | `str \| None` | `None` | BCC recipients. |
| `importance` | `str` | `"Normal"` | Mail importance. |

**Returns:** `dict` connector response for send operation.

**Example:**
```python
result = await o365.send_email(
    to="user@contoso.com",
    subject="Hello",
    body="Hi there!",
)
```

### `get_emails(folder: str = "Inbox", top: int = 10, unread_only: bool = False, subject_filter: str | None = None, from_filter: str | None = None)`

List emails in a folder.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `folder` | `str` | `"Inbox"` | Folder path. |
| `top` | `int` | `10` | Maximum number of messages. |
| `unread_only` | `bool` | `False` | If `True`, return only unread emails. |
| `subject_filter` | `str \| None` | `None` | Subject filter text. |
| `from_filter` | `str \| None` | `None` | Sender filter text. |

**Returns:** `list[dict]` message objects.

**Example:**
```python
result = await o365.get_emails(folder="Inbox", top=25, unread_only=True)
```

### `get_email(message_id: str)`

Get a single email by ID.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `message_id` | `str` | — | Message ID. |

**Returns:** `dict` message payload.

**Example:**
```python
result = await o365.get_email(message_id="AAMkAD...")
```

### `reply_to_email(message_id: str, body: str, reply_all: bool = False)`

Reply to an email.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `message_id` | `str` | — | Message to reply to. |
| `body` | `str` | — | Reply body text. |
| `reply_all` | `bool` | `False` | Reply to all recipients if `True`. |

**Returns:** `dict` connector response.

**Example:**
```python
result = await o365.reply_to_email(
    message_id="AAMkAD...",
    body="Thanks, received.",
    reply_all=True,
)
```

### `forward_email(message_id: str, to: str, comment: str | None = None)`

Forward an email.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `message_id` | `str` | — | Source message ID. |
| `to` | `str` | — | Forward recipients. |
| `comment` | `str \| None` | `None` | Optional forward comment. |

**Returns:** `dict` connector response.

**Example:**
```python
result = await o365.forward_email(
    message_id="AAMkAD...",
    to="reviewer@contoso.com",
    comment="Please review",
)
```

### `move_email(message_id: str, folder: str)`

Move an email to another folder.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `message_id` | `str` | — | Message ID to move. |
| `folder` | `str` | — | Destination folder path. |

**Returns:** `dict` connector response.

**Example:**
```python
result = await o365.move_email(message_id="AAMkAD...", folder="Archive")
```

### `mark_as_read(message_id: str, is_read: bool = True)`

Mark an email as read or unread.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `message_id` | `str` | — | Message ID. |
| `is_read` | `bool` | `True` | Read state to set. |

**Returns:** `dict` connector response.

**Example:**
```python
result = await o365.mark_as_read(message_id="AAMkAD...", is_read=False)
```

### `flag_email(message_id: str)`

Flag an email.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `message_id` | `str` | — | Message ID. |

**Returns:** `dict` connector response.

**Example:**
```python
result = await o365.flag_email(message_id="AAMkAD...")
```

### `delete_email(message_id: str)`

Delete an email.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `message_id` | `str` | — | Message ID. |

**Returns:** `dict` connector response.

**Example:**
```python
result = await o365.delete_email(message_id="AAMkAD...")
```

### `draft_email(to: str, subject: str, body: str, cc: str | None = None, bcc: str | None = None)`

Create an email draft.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `to` | `str` | — | Recipient list. |
| `subject` | `str` | — | Draft subject. |
| `body` | `str` | — | Draft body. |
| `cc` | `str \| None` | `None` | Draft CC recipients. |
| `bcc` | `str \| None` | `None` | Draft BCC recipients. |

**Returns:** `dict` created draft object/response.

**Example:**
```python
result = await o365.draft_email(
    to="user@contoso.com",
    subject="Draft",
    body="Initial content",
)
```

### `send_draft(message_id: str)`

Send an existing draft.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `message_id` | `str` | — | Draft message ID. |

**Returns:** `dict` connector response.

**Example:**
```python
result = await o365.send_draft(message_id="AAMkAD...")
```

### `get_attachment(message_id: str, attachment_id: str)`

Get a specific message attachment.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `message_id` | `str` | — | Message ID. |
| `attachment_id` | `str` | — | Attachment ID. |

**Returns:** `dict` attachment payload.

**Example:**
```python
result = await o365.get_attachment(
    message_id="AAMkAD...",
    attachment_id="AAMkAD...AAA=",
)
```

### `send_shared_mailbox_email(mailbox_address: str, to: str, subject: str, body: str, cc: str | None = None, bcc: str | None = None)`

Send an email from a shared mailbox.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `mailbox_address` | `str` | — | Shared mailbox address. |
| `to` | `str` | — | Recipients. |
| `subject` | `str` | — | Subject line. |
| `body` | `str` | — | Message body. |
| `cc` | `str \| None` | `None` | CC recipients. |
| `bcc` | `str \| None` | `None` | BCC recipients. |

**Returns:** `dict` connector response.

**Example:**
```python
result = await o365.send_shared_mailbox_email(
    mailbox_address="support@contoso.com",
    to="customer@contoso.com",
    subject="Support update",
    body="We have an update for you.",
)
```

### `assign_category(message_id: str, category: str)`

Assign an Outlook category to an email.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `message_id` | `str` | — | Message ID. |
| `category` | `str` | — | Category name. |

**Returns:** `dict` connector response.

**Example:**
```python
result = await o365.assign_category(message_id="AAMkAD...", category="Follow Up")
```

### `set_automatic_replies(settings: dict)`

Set automatic replies settings.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `settings` | `dict` | — | Automatic reply settings payload expected by Office 365 connector endpoint. |

**Returns:** `dict` connector response.

**Example:**
```python
result = await o365.set_automatic_replies(
    settings={
        "status": "alwaysEnabled",
        "externalAudience": "all",
        "internalReplyMessage": "Out of office",
        "externalReplyMessage": "Out of office",
    }
)
```

### Calendar Actions

### `get_events(calendar_id: str = "Calendar")`

Get events from a calendar.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `calendar_id` | `str` | `"Calendar"` | Calendar identifier/table. |

**Returns:** `list[dict]` event objects.

**Example:**
```python
result = await o365.get_events(calendar_id="Calendar")
```

### `create_event(subject: str, start: str, end: str, timezone: str, calendar_id: str = "Calendar", body: str | None = None, location: str | None = None, required_attendees: str | None = None, show_as: str = "busy")`

Create a calendar event.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `subject` | `str` | — | Event subject. |
| `start` | `str` | — | Start datetime string. |
| `end` | `str` | — | End datetime string. |
| `timezone` | `str` | — | Time zone value sent as `timeZone`. |
| `calendar_id` | `str` | `"Calendar"` | Calendar identifier/table. |
| `body` | `str \| None` | `None` | Optional event body. |
| `location` | `str \| None` | `None` | Optional location text. |
| `required_attendees` | `str \| None` | `None` | Optional required attendees list. |
| `show_as` | `str` | `"busy"` | Availability status for the event. |

**Returns:** `dict` created event/connector response.

**Example:**
```python
result = await o365.create_event(
    subject="Design review",
    start="2026-03-15T10:00:00",
    end="2026-03-15T11:00:00",
    timezone="(UTC) Coordinated Universal Time",
    required_attendees="a@contoso.com;b@contoso.com",
)
```

### `update_event(event_id: str, calendar_id: str = "Calendar", **fields)`

Update a calendar event.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `event_id` | `str` | — | Event ID to update. |
| `calendar_id` | `str` | `"Calendar"` | Calendar identifier/table. |
| `**fields` | `dict[str, Any]` | — | Fields to patch (for example `subject`, `start`, `end`, `location`, `showAs`). |

**Returns:** `dict` connector response.

**Example:**
```python
result = await o365.update_event(
    event_id="AAMkAGI2...",
    subject="Updated title",
    location="Teams",
)
```

### `delete_event(event_id: str, calendar_id: str = "Calendar")`

Delete a calendar event.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `event_id` | `str` | — | Event ID to delete. |
| `calendar_id` | `str` | `"Calendar"` | Calendar identifier. |

**Returns:** `dict` connector response.

**Example:**
```python
result = await o365.delete_event(event_id="AAMkAGI2...")
```

### `get_calendar_view(start: str, end: str, calendar_id: str = "Calendar")`

Get events between start and end datetimes.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start` | `str` | — | UTC start datetime. |
| `end` | `str` | — | UTC end datetime. |
| `calendar_id` | `str` | `"Calendar"` | Calendar identifier. |

**Returns:** `list[dict]` events in the requested window.

**Example:**
```python
result = await o365.get_calendar_view(
    start="2026-03-01T00:00:00Z",
    end="2026-03-31T23:59:59Z",
)
```

### `respond_to_invite(event_id: str, response: str)`

Respond to an event invitation.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `event_id` | `str` | — | Event invitation ID. |
| `response` | `str` | — | Response action (`accept`, `tentativelyAccept`, or `decline`). |

**Returns:** `dict` connector response.

**Example:**
```python
result = await o365.respond_to_invite(
    event_id="AAMkAGI2...",
    response="accept",
)
```

### `find_meeting_times(required_attendees: str | None = None, optional_attendees: str | None = None, duration_minutes: int = 30)`

Get suggested meeting times.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `required_attendees` | `str \| None` | `None` | Required attendee list. |
| `optional_attendees` | `str \| None` | `None` | Optional attendee list. |
| `duration_minutes` | `int` | `30` | Requested meeting duration. |

**Returns:** `dict` meeting suggestion payload.

**Example:**
```python
result = await o365.find_meeting_times(
    required_attendees="a@contoso.com;b@contoso.com",
    duration_minutes=45,
)
```

### `get_rooms()`

Get available rooms.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| — | — | — | No parameters. |

**Returns:** `dict` room list response.

**Example:**
```python
result = await o365.get_rooms()
```

### `get_room_lists()`

Get available room lists.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| — | — | — | No parameters. |

**Returns:** `dict` room list collections.

**Example:**
```python
result = await o365.get_room_lists()
```

### Contact Actions

### `get_contacts(folder: str = "Contacts")`

Get contacts from a contact folder.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `folder` | `str` | `"Contacts"` | Contact folder name/id. |

**Returns:** `list[dict]` contacts.

**Example:**
```python
result = await o365.get_contacts(folder="Contacts")
```

### `create_contact(given_name: str, surname: str | None = None, email: str | None = None, phone: str | None = None, folder: str = "Contacts")`

Create a contact.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `given_name` | `str` | — | Contact first name. |
| `surname` | `str \| None` | `None` | Contact last name. |
| `email` | `str \| None` | `None` | Primary email address. |
| `phone` | `str \| None` | `None` | Home phone number. |
| `folder` | `str` | `"Contacts"` | Target contact folder. |

**Returns:** `dict` created contact/response.

**Example:**
```python
result = await o365.create_contact(
    given_name="Alex",
    surname="Doe",
    email="alex@contoso.com",
)
```

### `get_contact(folder: str, contact_id: str)`

Get a single contact by ID.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `folder` | `str` | — | Contact folder name/id. |
| `contact_id` | `str` | — | Contact ID. |

**Returns:** `dict` contact payload.

**Example:**
```python
result = await o365.get_contact(folder="Contacts", contact_id="AAMkAG...")
```

### `update_contact(folder: str, contact_id: str, **fields)`

Update a contact.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `folder` | `str` | — | Contact folder name/id. |
| `contact_id` | `str` | — | Contact ID. |
| `**fields` | `dict[str, Any]` | — | Patch fields for contact properties. |

**Returns:** `dict` connector response.

**Example:**
```python
result = await o365.update_contact(
    folder="Contacts",
    contact_id="AAMkAG...",
    jobTitle="Engineering Manager",
)
```

### `delete_contact(folder: str, contact_id: str)`

Delete a contact by ID.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `folder` | `str` | — | Contact folder name/id. |
| `contact_id` | `str` | — | Contact ID. |

**Returns:** `dict` connector response.

**Example:**
```python
result = await o365.delete_contact(folder="Contacts", contact_id="AAMkAG...")
```

### Utility

### `get_calendars()`

Get available calendars.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| — | — | — | No parameters. |

**Returns:** `list[dict]` calendar entries.

**Example:**
```python
result = await o365.get_calendars()
```

### `http_request(method: str, uri: str)`

Send a raw Graph proxy HTTP request.

> **Currently unsupported via this SDK.** The Office 365 connector expects `Method` and `Uri` as HTTP headers, but ARM `dynamicInvoke` drops those headers. Calls usually fail with `Empty Http Method provided.`

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `method` | `str` | — | HTTP method (`GET`, `POST`, `PATCH`, `DELETE`, etc.). |
| `uri` | `str` | — | Full or relative Graph URI. |

**Returns:** `dict` raw connector response.

**Example:**
```python
from msgraph import GraphServiceClient

# Use Microsoft Graph directly for unsupported HTTP proxy scenarios.
graph = GraphServiceClient(...)
```

## Known Limitations

- `http_request()` is currently unusable through ARM `dynamicInvoke`; use typed client methods or Microsoft Graph directly.
