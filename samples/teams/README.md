# Sample: Microsoft Teams Triggers & Client

This sample demonstrates Teams triggers (channel messages, @mentions) and the typed client API.

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
teams = connectors.teams.get_client(connection_id="...")
my_teams = await teams.list_teams()  # get team IDs
channels = await teams.list_channels(team_id="...")  # get channel IDs
```
