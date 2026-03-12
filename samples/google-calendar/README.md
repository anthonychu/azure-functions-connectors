# Sample: Google Calendar Triggers + Client

This sample demonstrates Google Calendar action-based triggers and typed client usage.

## Prerequisites

- Python 3.10+
- Azure Functions Core Tools v4
- An Azure API Connection for Google Calendar (authenticated via OAuth)
- A managed identity or service principal with `Microsoft.Web/connections/dynamicInvoke/action`

## Setup

1. Copy `local.settings.json.template` to `local.settings.json`
2. Fill in your Google Calendar connection resource ID and calendar ID
3. Install dependencies: `pip install -r requirements.txt`
4. Run: `func start`

## Included functions

- `on_new_event`: fires for newly created calendar events (action-based polling)
- `on_updated_event`: fires for updated calendar events (action-based polling)
- `query_google_calendar`: timer sample that lists calendars and upcoming events

## Notes

- Native Google Calendar triggers are webhook-only and not compatible with dynamicInvoke.
- This SDK sample uses action-based polling, the same pattern used for Teams triggers.
- Use `primary` or your email address for `GOOGLE_CALENDAR_ID`.
