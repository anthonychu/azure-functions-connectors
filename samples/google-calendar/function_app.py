"""Google Calendar sample — action-based triggers and typed client usage."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

import azure.functions as func
import azure.functions_connectors as fc
from azure.functions_connectors._triggers.googlecalendar import GoogleCalendarEvent

app = func.FunctionApp()
connectors = fc.FunctionsConnectors(app)


@connectors.googlecalendar.new_event_trigger(
    connection_id="%GOOGLE_CALENDAR_CONNECTION_ID%",
    calendar_id="%GOOGLE_CALENDAR_ID%",
)
async def on_new_event(event: GoogleCalendarEvent):
    logging.info("[NEW EVENT] id=%s summary=%s start=%s", event.id, event.summary, event.start)


@connectors.googlecalendar.updated_event_trigger(
    connection_id="%GOOGLE_CALENDAR_CONNECTION_ID%",
    calendar_id="%GOOGLE_CALENDAR_ID%",
)
async def on_updated_event(event: GoogleCalendarEvent):
    logging.info(
        "[UPDATED EVENT] id=%s summary=%s updated=%s",
        event.id,
        event.summary,
        event.updated_at,
    )


@app.timer_trigger(schedule="0 */10 * * * *", arg_name="timer", run_on_startup=True)
async def query_google_calendar(timer: func.TimerRequest):
    del timer
    client = connectors.googlecalendar.get_client("%GOOGLE_CALENDAR_CONNECTION_ID%")

    calendars = await client.list_calendars()
    calendar_items = calendars.get("items", []) if isinstance(calendars, dict) else []
    logging.info("[LIST CALENDARS] fetched=%s", len(calendar_items))

    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
    now = datetime.now(timezone.utc).replace(microsecond=0)
    later = now + timedelta(days=7)

    events = await client.list_events(
        calendar_id=calendar_id,
        time_min=now.isoformat().replace("+00:00", "Z"),
        time_max=later.isoformat().replace("+00:00", "Z"),
        max_results=10,
    )
    event_items = events.get("items", []) if isinstance(events, dict) else []
    logging.info("[LIST EVENTS] calendar=%s fetched=%s", calendar_id, len(event_items))
