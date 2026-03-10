# Teams Trigger Polling Limitation

## Summary

The Microsoft Teams connector's batch polling triggers (e.g., `OnNewChannelMessage`,
`OnNewChannelMessageMentioningMe`) have a **connector-side bug** that prevents them from
working via `dynamicInvoke`. The trigger correctly detects new items, but then **crashes**
while computing the next cursor state, returning a 502 BadGateway error.

## Details

### Tested Trigger

- **Path:** `/trigger/beta/teams/{teamId}/channels/{channelId}/messages`
- **Connection:** Authenticated Teams API connection in Azure (westus)
- **operationId:** `OnNewChannelMessage`

### Behavior

1. **Fresh poll (no cursor):** Returns 202 Accepted with a `Location` header containing a
   `triggerState` skiptoken. No items in body. ✅
2. **Poll with cursor (no new items):** Returns 202 Accepted with updated `Location` header. ✅
3. **Poll with cursor (new items exist):** Returns **502 BadGateway** with error:
   `"Unable to compute iso trigger state."` The error body includes the actual message items
   that were found, confirming the trigger DID detect them. ❌

### Error Detail

```json
{
  "error": {
    "code": 502,
    "message": "Unable to compute iso trigger state.\nItems:\n[\n  {\n    \"replyToId\": null,\n    \"etag\": \"1773186410636\",\n    \"messageType\": \"message\",\n    \"createdDateTime\": \"2026-03-10T23:46:50.636Z\",\n    ..."
  }
}
```

The connector is finding items but failing to build the next ISO-formatted `triggerState`
cursor from the message data. This is similar to the calendar trigger's `triggerstate`
cursor issue, but in that case the fix was on our side (key casing). Here the failure is
inside the connector's internal cursor computation.

### Cursor Format

The `Location` header contains:
```
triggerState=$skiptoken~-9XhG0rwHHVc1gT8KCEuMnc1Cct4...
```

Cursor comparison across connectors:
- Office 365 email: `LastPollInformation` (ISO timestamp)
- Office 365 calendar: `triggerstate` (lowercase, ISO timestamp)
- Teams: `triggerState` (camelCase S, opaque skiptoken blob)

The cursor is correctly stored and passed back by our SDK. Additional validation showed:

- `triggerState=<skiptoken...>`: detects items, then fails with 502 (`Unable to compute iso trigger state`).
- `triggerstate=<skiptoken...>`: returns 202 but **suppresses items** (no crash, but no events delivered).
- `LastPollInformation=<iso>`: returns 202 with no items for this trigger.

So there is no safe query-shape workaround that both avoids the error and returns items.

### Other Teams Batch Triggers

| Trigger | Status |
|---------|--------|
| `OnNewChannelMessage` | 502 when items found (cursor bug) |
| `OnNewChannelMessageMentioningMe` | Untested with actual items (likely same bug) |
| `OnGroupMembershipAdd` | Returns 404 NotFound |
| `OnGroupMembershipRemoval` | Returns 404 NotFound |

### What Works

Teams connector **actions** (non-trigger endpoints) work fine via `dynamicInvoke`:
- `GET /beta/teams` — list teams ✅
- `GET /beta/teams/{teamId}/channels` — list channels ✅
- `POST /beta/teams/{teamId}/channels/{channelId}/messages` — post message ✅
- All other action endpoints — ✅

### Workarounds

Since the connector's polling trigger is broken server-side, alternatives are:

1. **Timer + Teams client** — Use a timer function with `TeamsClient.get_messages_from_channel()`
   and track state manually (last seen message timestamp/ID). This is the simplest and uses the
   same connection. **Recommended.**
2. **Direct Graph API polling** — Use `GET /beta/teams/{teamId}/channels/{channelId}/messages/delta`
   via Microsoft Graph directly. Requires its own auth (not the connector).
3. **Webhook subscriptions** — Create webhook subscriptions via the connector's webhook trigger
   endpoints (e.g., `WebhookNewMessageTrigger`). Requires a public endpoint and subscription
   lifecycle management. Complex.

### Recommendation

- Teams support in the SDK focuses on the **client** (21 action methods) which all work correctly
- Teams trigger methods have been removed from the SDK since they cannot work
- The timer + client workaround is documented as the recommended approach
- Trigger methods can be re-added if the connector bug is fixed

### Investigation Notes (2026-03-10)

Validated against live `dynamicInvoke` calls with the Teams connection:

- `triggerState` in `queries` is the only form that attempts to return new items, and it fails when items exist.
- Putting `triggerState` in the path query (instead of `queries`) yields `NotFound`.
- Adding `$top`, adding `x-ms-operation-context`, and URL-encoding the skiptoken do not fix the failure.
- Swagger confirms trigger metadata is already configured for ISO extraction:
  - `x-ms-dev-triggerDateFormat: "iso"`
  - `x-ms-dev-triggerValuePath: "createdDateTime"`
  - `x-ms-dev-triggerValueCollection: "value"`
  - `x-ms-trigger: "batch"`

Conclusion: this is a connector-side trigger-state computation bug, not an SDK request-shaping issue.
