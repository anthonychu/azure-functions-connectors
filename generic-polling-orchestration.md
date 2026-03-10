# Generic Connector Polling Orchestration

A Durable Functions eternal orchestration that polls any Azure managed connector trigger using the cursor-based `x-ms-trigger: batch` pattern. Works with any connector (Office 365, Salesforce, SharePoint, etc.) without code changes — just different input.

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│  Eternal Orchestrator (one per trigger)             │
│                                                     │
│  1. Call PollTrigger activity                        │
│  2. If 200 → call DispatchItems activity            │
│     If 202 → increase backoff                       │
│  3. Wait (timer with exponential backoff)           │
│  4. ContinueAsNew with updated cursor + interval    │
└─────────────────────────────────────────────────────┘
         │                          │
         ▼                          ▼
  ┌──────────────┐         ┌──────────────────┐
  │ PollTrigger  │         │ DispatchItems    │
  │ (activity)   │         │ (activity)       │
  │              │         │                  │
  │ dynamicInvoke│         │ POST to callback │
  │ → ARM API    │         │ or enqueue       │
  └──────────────┘         └──────────────────┘
         │
         ▼
  ┌──────────────────────┐
  │ Azure API Connection │
  │ (office365, etc.)    │
  └──────────────────────┘
```

## Orchestrator Input

```json
{
  "connectionId": "/subscriptions/{subId}/resourceGroups/{rg}/providers/Microsoft.Web/connections/{name}",
  "triggerPath": "/Mail/OnNewEmail",
  "triggerQueries": { "folderPath": "Inbox" },
  "instance_id": "ctp:office365:mail-onnew:a3f8b2c1",
  "structural_hash": "abc123",
  "runtime_hash": "def456",
  "minInterval": 2,
  "maxInterval": 300
}
```

### Example Inputs for Different Connectors

**Office 365 — new emails:**
```json
{
  "connectionId": ".../connections/office365",
  "triggerPath": "/Mail/OnNewEmail",
  "triggerQueries": { "folderPath": "Inbox" }
}
```

**Office 365 — calendar changes:**
```json
{
  "connectionId": ".../connections/office365",
  "triggerPath": "/datasets/calendars/v3/tables/{calendarId}/onnewitems",
  "triggerQueries": {}
}
```

**Salesforce — new leads:**
```json
{
  "connectionId": ".../connections/salesforce",
  "triggerPath": "/datasets/default/tables/Lead/onnewitems",
  "triggerQueries": {}
}
```

**Salesforce — modified contacts:**
```json
{
  "connectionId": ".../connections/salesforce",
  "triggerPath": "/datasets/default/tables/Contact/onupdateditems",
  "triggerQueries": { "$select": "Name,Email,Phone" }
}
```

**SharePoint — new list items:**
```json
{
  "connectionId": ".../connections/sharepointonline",
  "triggerPath": "/datasets/{siteUrl}/tables/{listId}/onnewitems",
  "triggerQueries": {}
}
```

## Activity Functions

### 1. PollTrigger

Calls the connector's polling trigger via ARM `dynamicInvoke`.

**Input:**
```json
{
  "connectionId": "/subscriptions/.../connections/office365",
  "triggerPath": "/Mail/OnNewEmail",
  "triggerQueries": { "folderPath": "Inbox" },
  "cursor": null
}
```

**Logic:**
```
1. Build queries = { ...triggerQueries }
2. If cursor is not null:
     queries["LastPollInformation"] = cursor
3. Call ARM:
     POST {connectionId}/dynamicInvoke?api-version=2016-06-01
     Body: {
       "request": {
         "method": "GET",
         "path": triggerPath,
         "queries": queries
       }
     }
4. Extract new cursor from response Location header:
     cursor = URL(response.headers.Location).searchParams.get("LastPollInformation")
5. Return {
     status: response.statusCode (200 or 202),
     items: response.body (array of items, or empty),
     cursor: cursor
   }
```

**Auth:** Uses `DefaultAzureCredential` to get an ARM token. The Function App's managed identity needs `Microsoft.Web/connections/dynamicInvoke/action` + `Microsoft.Web/connections/read` on the connection resource.

### 2. ProcessItem

Processes a single item by calling the registered handler. Supports sync and async.

**Input:**
```json
{
  "instance_id": "ctp:office365:mail-onnew:a3f8b2c1",
  "item": { ... }
}
```

**Logic:**
```
1. Look up handler from _handler_registry by instance_id
2. If handler not found → log warning, drop item (no retry)
3. If async handler → await handler(item)
4. If sync handler → handler(item)
```

## Orchestrator (Eternal)

```python
MAX_ITEMS_PER_POLL = 100

def orchestrator(ctx):
    input = ctx.get_input()
    cursor = input.get("cursor")
    interval = input.get("currentInterval", input.get("minInterval", 2))
    min_interval = input.get("minInterval", 2)
    max_interval = input.get("maxInterval", 300)

    # Step 1: Poll the trigger
    poll_result = yield ctx.call_activity("PollTrigger", {
        "connectionId": input["connectionId"],
        "triggerPath": input["triggerPath"],
        "triggerQueries": input.get("triggerQueries", {}),
        "cursor": cursor
    })

    # Always update cursor
    cursor = poll_result["cursor"]

    if poll_result["status"] == 200 and poll_result["items"]:
        # Step 2a: New items found — fan out with bounded concurrency
        items = poll_result["items"]
        instance_id = input["instance_id"]
        for chunk in batched(items, MAX_ITEMS_PER_POLL):
            tasks = [ctx.call_activity("ProcessItem",
                        {"instance_id": instance_id, "item": item})
                     for item in chunk]
            yield ctx.task_all(tasks)
        interval = min_interval
    else:
        # Step 2b: Nothing new — exponential backoff
        # Honor Retry-After from connector if present
        retry_after = poll_result.get("retryAfter")
        if retry_after:
            interval = max(interval, retry_after)
        else:
            interval = min(interval * 2, max_interval)

    # Step 3: Wait
    deadline = ctx.current_utc_datetime + timedelta(seconds=interval)
    yield ctx.create_timer(deadline)

    # Step 4: Loop forever with updated state
    ctx.continue_as_new({
        **input,
        "cursor": cursor,
        "currentInterval": interval
    })
```

## Backoff Behavior

```
poll → 202 (nothing) → wait 2s
poll → 202 (nothing) → wait 4s
poll → 202 (nothing) → wait 8s
poll → 202 (nothing) → wait 16s
poll → 202 (nothing) → wait 32s
...
poll → 202 (nothing) → wait 300s (capped)
poll → 200 (items!)  → dispatch → reset to 2s
poll → 202 (nothing) → wait 2s
poll → 202 (nothing) → wait 4s
...
```

Typical latency:
- **Active period:** ~2 seconds (min interval)
- **Idle period:** up to 5 minutes (max interval)
- **Transition:** one poll cycle to detect new items after idle

## State Management

Only two values are persisted across `ContinueAsNew` cycles:

| State | Source | Purpose |
|-------|--------|---------|
| `cursor` | `Location` header from poll response | Tracks which items have been returned |
| `currentInterval` | Calculated by orchestrator | Backoff state |

Everything else (connectionId, triggerPath, etc.) is static config passed through.

## Instance Management

Use a deterministic instance ID to prevent duplicate orchestrations for the same trigger:

```
instance_id = f"poll:{connection_name}:{trigger_path_hash}"
```

Example: `poll:office365:mail-onnew-inbox`

To start:
```python
client.start_new("GenericPollingOrchestrator", instance_id, input)
```

To stop: terminate the instance or have it check a "stop" flag in external state.

## RBAC / Permissions

The Function App's managed identity needs a custom role on the connection resource(s):

```json
{
  "Name": "API Connection Invoker",
  "Actions": [
    "Microsoft.Web/connections/dynamicInvoke/action",
    "Microsoft.Web/connections/read"
  ]
}
```

Assign scoped to the resource group or individual connection resources. See [webhook notes](./office365-webhook-notes.md) for detailed RBAC guidance.

## Optional Enhancement: Webhook Accelerator

For connectors that support poke webhooks (like Office 365), you can optionally add a webhook subscription that resets the backoff interval to 0 when a poke arrives:

```
Poke received → send external event to orchestrator → orchestrator wakes up immediately
```

This gives you near-instant response during webhook availability, with automatic fallback to polling if the webhook expires or fails. The cursor handles dedup regardless of how the poll is triggered.

## What's Generic

Everything. The orchestrator and both activities know nothing about any specific connector. To monitor a new trigger, just start a new orchestrator instance with different input. No code changes needed.

| Component | Connector-specific? |
|-----------|-------------------|
| Orchestrator | ❌ Generic |
| PollTrigger activity | ❌ Generic (calls dynamicInvoke) |
| DispatchItems activity | ❌ Generic (POSTs to callback) |
| Input config | ✅ Different per trigger |
