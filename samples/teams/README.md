# Sample: Microsoft Teams Client

This sample demonstrates using the Teams client API on a timer to periodically
check for new channel messages.

> **Note:** Teams polling triggers are not currently supported due to a
> connector-side bug. This sample uses a timer + client workaround instead.

## Prerequisites

- Python 3.9+
- Azure Functions Core Tools v4
- An Azure API Connection for Microsoft Teams (authenticated via OAuth)

## Setup

1. Copy `local.settings.json.template` to `local.settings.json`
2. Fill in your Teams connection resource ID, team ID, and channel ID
3. Install dependencies: `pip install -r requirements.txt`
4. Run: `func start`

To find your team and channel IDs, use the Teams client:
```python
client = connectors.teams.get_client(connection_id="...")
my_teams = await client.list_teams()  # get team IDs
channels = await client.list_channels(team_id="...")  # get channel IDs
```
