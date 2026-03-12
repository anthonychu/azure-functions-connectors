# Sample: Microsoft Teams Triggers + Client

This sample demonstrates Teams channel triggers and Teams client API usage.

Teams channel message triggers are implemented with action-based polling
(`get_messages`) so they work even when native Teams polling trigger endpoints
are unavailable.

## Prerequisites

- Python 3.9+
- Azure Functions Core Tools v4
- An Azure API Connection for Microsoft Teams (authenticated via OAuth)

## Setup

1. Copy `local.settings.json.template` to `local.settings.json`
2. Fill in your Teams connection resource ID, team ID, and channel ID
3. Install dependencies: `pip install -r requirements.txt`
4. Run: `func start`

## Included functions

- `on_channel_message`: fires on new channel posts
- `on_mention`: fires when your account is mentioned in a channel post
- `query_teams`: periodic Teams client usage example (list channels)

To find your team and channel IDs, use the Teams client:
```python
client = connectors.teams.get_client(connection_id="...")
my_teams = await client.list_teams()  # get team IDs
channels = await client.list_channels(team_id="...")  # get channel IDs
```
