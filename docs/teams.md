# Microsoft Teams Connector API Documentation

## Table of Contents

- [Overview](#overview)
- [Finding Your IDs](#finding-your-ids)
- [Triggers](#triggers)
- [Models](#models)
  - [TeamsMessage](#teamsmessage)
  - [TeamsChannel](#teamschannel)
- [Client](#client)
  - [Messages](#messages)
  - [Channels](#channels)
  - [Teams](#teams)
  - [Chats](#chats)
  - [Tags](#tags)
  - [Members](#members)
  - [Meetings](#meetings)
- [Known Limitations](#known-limitations)

## Overview

The Teams connector currently provides:

- Typed **triggers** for Teams channel messages:
  - `new_channel_message_trigger(...)`
  - `channel_mention_trigger(...)`
- A typed **action client** (`TeamsClient`) for Teams messages, channels, chats, tags, members, and meetings.
- Typed helper models:
  - `TeamsMessage`
  - `TeamsChannel`
- A `connectors.teams.get_client(...)` helper for creating the typed client from `FunctionsConnectors`.

```python
teams = connectors.teams.get_client(connection_id="%TEAMS_CONNECTION_ID%")
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

Store it as an app setting (e.g., `TEAMS_CONNECTION_ID`) and reference it with `%TEAMS_CONNECTION_ID%` in your trigger decorators.

### Team ID and Channel ID

Use the Teams client to discover your team and channel IDs:

```python
client = connectors.teams.get_client("%TEAMS_CONNECTION_ID%")

# List your teams
teams = await client.list_teams()
for t in teams:
    print(f"{t.get('displayName')}: {t.get('id')}")

# List channels in a team
channels = await client.list_channels(team_id="your-team-id")
for ch in channels:
    print(f"{ch.get('displayName')}: {ch.get('id')}")
```

Or use the CLI:
```bash
CONN_ID="/subscriptions/.../providers/Microsoft.Web/connections/teams"

# List teams
az rest --method POST \
  --url "https://management.azure.com${CONN_ID}/dynamicInvoke?api-version=2016-06-01" \
  --body '{"request":{"method":"GET","path":"/beta/me/joinedTeams","queries":{}}}' \
  --query 'response.body.value[].{name:displayName, id:id}' -o tsv

# List channels (replace TEAM_ID)
az rest --method POST \
  --url "https://management.azure.com${CONN_ID}/dynamicInvoke?api-version=2016-06-01" \
  --body '{"request":{"method":"GET","path":"/beta/groups/TEAM_ID/channels","queries":{}}}' \
  --query 'response.body.value[].{name:displayName, id:id}' -o tsv
```

Team IDs look like: `f9beb78b-5f1b-4819-a5a0-dabdb6805b12`
Channel IDs look like: `19:abc123...@thread.tacv2`


## Triggers

Teams trigger decorators are available on `connectors.teams`:

- `new_channel_message_trigger(connection_id, team_id, channel_id)` — fires on new top-level posts in a channel.
- `channel_mention_trigger(connection_id, team_id, channel_id)` — fires on new top-level posts that mention your account.
All trigger methods accept optional `min_interval` (default: 60) and `max_interval` (default: 300) parameters to control polling frequency in seconds.

```python
from azure.functions_connectors import TeamsMessage

@connectors.teams.new_channel_message_trigger(
    connection_id="%TEAMS_CONNECTION_ID%",
    team_id="%TEAMS_TEAM_ID%",
    channel_id="%TEAMS_CHANNEL_ID%",
)
async def on_channel_message(message: TeamsMessage):
    print("New channel post:", message.body_preview)

@connectors.teams.channel_mention_trigger(
    connection_id="%TEAMS_CONNECTION_ID%",
    team_id="%TEAMS_TEAM_ID%",
    channel_id="%TEAMS_CHANNEL_ID%",
)
async def on_channel_mention(message: TeamsMessage):
    print("Mentioned in channel:", message.body_preview)
```

> **Note:** Triggers fire for **top-level channel posts only**. Replies within threads and chat message triggers are not currently supported.

## Models

### `TeamsMessage`

Typed wrapper for Teams message payloads.

| Property | Type | Description |
|----------|------|-------------|
| `id` | `str` | Message ID. |
| `body` | `dict \| str` | Raw message body payload. |
| `body_preview` | `str` | Body preview text. |
| `sender` | `str` | Sender display name, email, or ID when available. |
| `created_at` | `str` | Message creation timestamp. |
| `message_type` | `str` | Graph message type. |
| `subject` | `str` | Subject, when present. |
| `importance` | `str` | Importance value. |
| `web_url` | `str` | Browser URL for the message. |
| `channel_identity` | `dict` | Channel identity payload. |
| `attachments` | `list` | Message attachments. |

### `TeamsChannel`

Typed wrapper for Teams channel payloads.

| Property | Type | Description |
|----------|------|-------------|
| `id` | `str` | Channel ID. |
| `name` | `str` | Channel display name. |
| `description` | `str` | Channel description. |
| `membership_type` | `str` | Membership type (`standard`, `private`, `shared`). |

## Client

Create the typed client:

```python
client = connectors.teams.get_client("%TEAMS_CONNECTION_ID%")
```

### Messages

#### `post_message(team_id: str, channel_id: str, body: str, subject: str | None = None)`
```python
await client.post_message(
    team_id="%TEAMS_TEAM_ID%",
    channel_id="%TEAMS_CHANNEL_ID%",
    body="<p>Hello from Azure Functions</p>",
)
```

#### `reply_to_message(team_id: str, channel_id: str, message_id: str, body: str)`
```python
await client.reply_to_message(
    team_id="%TEAMS_TEAM_ID%",
    channel_id="%TEAMS_CHANNEL_ID%",
    message_id="<message-id>",
    body="<p>Thanks!</p>",
)
```

#### `get_messages(team_id: str, channel_id: str)`
```python
messages = await client.get_messages(
    "%TEAMS_TEAM_ID%",
    "%TEAMS_CHANNEL_ID%",
)
```

#### `get_message_replies(team_id: str, channel_id: str, message_id: str, top: int = 20)`
```python
replies = await client.get_message_replies(
    "%TEAMS_TEAM_ID%",
    "%TEAMS_CHANNEL_ID%",
    "<message-id>",
)
```

#### `get_message_details(message_id: str, thread_type: str = "channel")`
```python
details = await client.get_message_details("<message-id>")
```

### Channels

#### `list_channels(team_id: str)`
```python
channels = await client.list_channels("%TEAMS_TEAM_ID%")
```

#### `list_all_channels(team_id: str)`
```python
all_channels = await client.list_all_channels("%TEAMS_TEAM_ID%")
```

#### `create_channel(team_id: str, name: str, description: str | None = None)`
```python
created = await client.create_channel(
    team_id="%TEAMS_TEAM_ID%",
    name="Project Updates",
    description="Announcements and project status",
)
```

#### `get_channel(team_id: str, channel_id: str)`
```python
channel = await client.get_channel("%TEAMS_TEAM_ID%", "%TEAMS_CHANNEL_ID%")
```

### Teams

#### `list_teams()`
```python
teams = await client.list_teams()
```

#### `create_team(name: str, description: str, visibility: str = "Public")`
```python
created = await client.create_team(
    name="Contoso Launch",
    description="Launch coordination team",
)
```

#### `get_team(team_id: str)`
```python
team = await client.get_team("%TEAMS_TEAM_ID%")
```

### Chats

#### `list_chats(chat_type: str = "all")`
```python
chats = await client.list_chats(chat_type="meeting")
```

#### `create_chat(members: str, topic: str | None = None)`
```python
chat = await client.create_chat(
    members="user-1-guid;user-2-guid",
    topic="Incident bridge",
)
```

### Tags

#### `list_tags(team_id: str)`
```python
tags = await client.list_tags("%TEAMS_TEAM_ID%")
```

#### `create_tag(team_id: str, name: str, members: str)`
```python
tag = await client.create_tag(
    team_id="%TEAMS_TEAM_ID%",
    name="OnCall",
    members="user-guid-1;user-guid-2",
)
```

#### `delete_tag(team_id: str, tag_id: str)`
```python
await client.delete_tag("%TEAMS_TEAM_ID%", "<tag-id>")
```

#### `add_member_to_tag(team_id: str, tag_id: str, user_id: str)`
```python
await client.add_member_to_tag("%TEAMS_TEAM_ID%", "<tag-id>", "<user-id>")
```

### Members

#### `add_member(team_id: str, user_id: str, owner: bool = False)`
```python
await client.add_member("%TEAMS_TEAM_ID%", "<user-id>", owner=True)
```

#### `get_mention_token(user_id: str)`
```python
mention = await client.get_mention_token("<user-id>")
```

### Meetings

#### `create_meeting(subject: str, start: str, end: str, timezone: str, calendar_id: str = "Calendar", required_attendees: str | None = None, body: str | None = None)`
```python
meeting = await client.create_meeting(
    subject="Weekly Sync",
    start="2026-03-10T18:00:00",
    end="2026-03-10T18:30:00",
    timezone="(UTC) Coordinated Universal Time",
    required_attendees="user1@contoso.com;user2@contoso.com",
)
```

## Known Limitations

- **Trigger scope:** only top-level channel posts and @mentions are supported. Replies within threads and chat messages are not currently available.
- **`http_request()` is not supported:** the connector requires parameters as HTTP headers that cannot be forwarded by this SDK. Use the typed client methods or the Microsoft Graph SDK for unsupported endpoints.
