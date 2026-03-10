# Office 365 Connector Webhook — New Email Notifications

This document describes how to subscribe to new email notifications using the Office 365 managed connector's webhook (poke) subscription, manage the subscription lifecycle, and handle incoming notifications.

All connector operations are called via the ARM dynamic invoke endpoint:

```
POST https://management.azure.com/subscriptions/{subId}/resourceGroups/{rg}/providers/Microsoft.Web/connections/{connectionName}/dynamicInvoke?api-version=2016-06-01
```

**Prerequisites:**
- An Azure API Connection resource for the `office365` managed API, authenticated via OAuth consent
- An ARM bearer token (e.g., from `az account get-access-token` or managed identity)
- A publicly accessible HTTPS endpoint to receive webhook notifications

---

## RBAC Permissions for Managed Identity

All operations (subscribe, renew, delete, fetch) use the same ARM `dynamicInvoke` endpoint, so you only need one set of permissions.

### Minimum Custom Role (Recommended)

```json
{
  "Name": "API Connection Invoker",
  "Description": "Allows invoking actions on an API connection via dynamicInvoke",
  "Actions": [
    "Microsoft.Web/connections/dynamicInvoke/action",
    "Microsoft.Web/connections/read"
  ],
  "AssignableScopes": [
    "/subscriptions/{subId}/resourceGroups/{rg}/providers/Microsoft.Web/connections/{connectionName}"
  ]
}
```

Assign to your managed identity scoped to the specific connection resource:

```bash
az role definition create --role-definition role.json
az role assignment create \
  --assignee <managed-identity-object-id> \
  --role "API Connection Invoker" \
  --scope "/subscriptions/{subId}/resourceGroups/{rg}/providers/Microsoft.Web/connections/office365"
```

### Alternative: Built-in Role (Broader)

If you can't create custom roles, use **Logic App Contributor** scoped to the connection resource:

```bash
az role assignment create \
  --assignee <managed-identity-object-id> \
  --role "Logic App Contributor" \
  --scope "/subscriptions/{subId}/resourceGroups/{rg}/providers/Microsoft.Web/connections/office365"
```

This grants `Microsoft.Web/connections/*` which is broader than needed but limits blast radius via resource-scoped assignment.

### ⚠️ Caution: Logic App Contributor on a Resource Group

If you scope **Logic App Contributor** to a resource group (instead of a specific connection), be aware of what else it grants:

| Permission | Risk |
|------------|------|
| `Microsoft.Web/connections/*` | ✅ What you need |
| `Microsoft.Web/sites/functions/listSecrets/action` | ⚠️ Can read Function App keys |
| `Microsoft.Storage/storageAccounts/listkeys/action` | ⚠️ **Can get storage account keys** (full data access) |
| `Microsoft.Storage/storageAccounts/read` | Low risk — read-only metadata |
| `Microsoft.Logic/*` | Only matters if Logic Apps exist in the RG |
| `Microsoft.Web/customApis/*` | Only matters if custom APIs exist in the RG |
| `Microsoft.Web/connectionGateways/*` | Only matters if on-premises gateways exist in the RG |
| `Microsoft.Web/serverFarms/join/action` | Can join App Service plans |

**If the RG contains a Function App + storage account** (common pattern), the managed identity could list storage keys and read Function secrets. Use the **custom role** instead when sharing a resource group with other resources.

---

## 1. Creating a Subscription

**Connector endpoint:** `POST /{connectionId}/GraphMailSubscriptionPoke/$subscriptions`

**Request:**

```json
{
  "request": {
    "method": "POST",
    "path": "/GraphMailSubscriptionPoke/$subscriptions",
    "queries": {
      "folderPath": "Inbox",
      "importance": "Any",
      "fetchOnlyWithAttachment": false
    },
    "body": {
      "NotificationUrl": "https://your-callback-url"
    }
  }
}
```

**Filter options (all optional):**

| Parameter | Type | Values | Default |
|-----------|------|--------|---------|
| `folderPath` | string | Mail folder name (e.g., `Inbox`) | Inbox |
| `importance` | string | `Any`, `Low`, `Normal`, `High` | Any |
| `fetchOnlyWithAttachment` | boolean | `true` / `false` | false |

**Response (201 Created):**

```json
{
  "id": "82f94813-bcdb-4b1b-b576-6b8912dbb951",
  "notificationType": "webhook",
  "notificationUrl": "https://your-callback-url",
  "renewInterval": "PT1H",
  "resource": "https://logic-apis-westus.azure-apim.net/apim/office365/{connectionId}/GraphMailSubscriptionPoke/$subscriptions?folderPath=Inbox"
}
```

**Location header (important — contains the options token):**

```
https://logic-apis-westus.azure-apim.net/apim/office365/{connectionId}/MailSubscription/$subscriptions/{subscriptionId}?options={base64-encoded-options-token}
```

### What to Persist

You **must** save two values from the create response for future renew/delete calls:

| Value | Source | Example |
|-------|--------|---------|
| `subscriptionId` | `response.body.id` | `82f94813-bcdb-4b1b-b576-6b8912dbb951` |
| `optionsToken` | Query param `options` from `Location` header | `eyJGb2xkZXJQYXRo...` |

Extract the options token:
```
optionsToken = new URL(response.headers.Location).searchParams.get("options")
```

### Options Token Explained

The options token is a base64-encoded JSON object that captures the subscription config. Example decoded:

```json
{
  "FolderPath": "Inbox",
  "Importance": 0,
  "HasAttachment": 0,
  "IsOnNewMentioningMeEmailNotification": false,
  "IsOnFlaggedEmailNotification": false,
  "IsPokeNotification": true,
  "IsGraphApi": true,
  "OutlookApiVersion": 1,
  "GraphApiVersion": 1
}
```

This token is deterministic — the same create parameters always produce the same token. However, it's safest to save it directly from the response rather than reconstructing it.

---

## 2. Validation Handshake

When creating the subscription, the service sends a validation request to your callback URL:

- **Method:** `GET` (or `POST`)
- **Query param:** `?validationToken=<token-string>`

Your endpoint **must** respond with:

- **Status:** `200`
- **Content-Type:** `text/plain`
- **Body:** The `validationToken` value echoed back verbatim

Example handler (Node.js):
```js
const url = new URL(req.url, `http://localhost:${PORT}`);
const validationToken = url.searchParams.get("validationToken");
if (validationToken) {
  res.writeHead(200, { "Content-Type": "text/plain" });
  res.end(validationToken);
  return;
}
```

If validation fails, the subscription will not be created.

---

## 3. Receiving Notifications

When a new email arrives in the subscribed folder, Azure sends a poke notification:

- **Method:** `POST`
- **Body:** Empty (`Content-Length: 0`)
- **Notable headers:** `x-ms-client-request-id`

This is a **poke notification** — it tells you something happened but does **not** include the email data. You must fetch the emails separately (see next section).

Your endpoint should respond with `200 OK`.

> **Note:** A single email may generate multiple pokes (we observed ~2 per subscription). If you create multiple subscriptions, each fires independently. Your fetch logic must handle duplicates (see below).

---

## 4. Fetching Emails After a Notification (Polling Trigger with Cursor)

**Use `GET /Mail/OnNewEmail` instead of `GET /v3/Mail`.** This endpoint supports a cursor-based watermark that tracks which emails have already been returned, so you only get new emails each time.

### How the Cursor Works

The cursor is a base64-encoded JSON watermark passed via the `LastPollInformation` query parameter. It contains timestamps that track where you left off:

```json
{
  "LastReceivedMailTime": "2026-03-10T06:24:50.508Z",
  "LastCreatedMailTime": "2026-03-10T06:24:50.508Z",
  "LastMessageId": null,
  "LastInternetMessageId": null
}
```

You receive a new cursor in the **`Location` response header** on every call. Always save it and pass it on the next call.

### Step-by-Step

**Step 1: Establish a baseline cursor (first call, no cursor yet):**

```json
{
  "request": {
    "method": "GET",
    "path": "/Mail/OnNewEmail",
    "queries": {
      "folderPath": "Inbox"
    }
  }
}
```

Response: `202 Accepted` (no emails — establishing baseline)

```
Location: .../Mail/OnNewEmail?folderPath=Inbox&LastPollInformation=eyJMYXN0...
Retry-After: 15
```

Extract and save the cursor:
```
cursor = new URL(response.headers.Location).searchParams.get("LastPollInformation")
```

**Step 2: Fetch new emails (after poke notification, with cursor):**

```json
{
  "request": {
    "method": "GET",
    "path": "/Mail/OnNewEmail",
    "queries": {
      "folderPath": "Inbox",
      "LastPollInformation": "<cursor from previous response>"
    }
  }
}
```

If new emails exist: `200 OK` with email array + new cursor in `Location` header.
If nothing new: `202 Accepted` with empty body + updated cursor.

**Step 3: Save the new cursor** from the `Location` header for the next call.

### Response Status Codes

| Status | Meaning | Body | Action |
|--------|---------|------|--------|
| **200 OK** | New emails found | Array of email objects | Process emails, save new cursor |
| **202 Accepted** | Nothing new | Empty | Save new cursor, wait for next poke |

### Key Properties

- **Cursor is stateless** — same cursor always returns the same results (safe to retry)
- **Cursor advances via the response** — each response includes a new cursor that skips previously returned emails
- **No mark-as-read needed for dedup** — the cursor handles dedup by timestamp
- **Duplicate pokes are harmless** — first call returns the email, subsequent calls with the updated cursor return nothing

### Comparison: `GET /Mail/OnNewEmail` vs `GET /v3/Mail`

| | `GET /Mail/OnNewEmail` (Recommended) | `GET /v3/Mail` |
|---|---|---|
| **Dedup** | Built-in via cursor | Must track `isRead` yourself |
| **Returns** | Only emails since cursor | All emails matching filters |
| **State** | `LastPollInformation` cursor | None |
| **Multiple calls** | Safe — cursor prevents re-processing | Returns same emails every time |

### State to Persist

Your app only needs to persist **one value**: the latest `LastPollInformation` cursor string.

---

## 5. Alternative: Fetching Emails Without Cursor

If you prefer a simpler approach without cursor management, you can use `GET /v3/Mail`:

```json
{
  "request": {
    "method": "GET",
    "path": "/v3/Mail",
    "queries": {
      "folderPath": "Inbox",
      "fetchOnlyUnread": true,
      "top": 10
    }
  }
}
```

This returns all unread emails every time. You must mark emails as read after processing to avoid reprocessing them on the next poke.

---

## 6. Renewing a Subscription

Subscriptions expire after **1 hour (`PT1H`)**. This interval is fixed by the connector and cannot be changed — the connector ignores any `renewInterval` value you pass. You must set up a timer/cron to renew every ~50 minutes.

**Connector endpoint:** `PATCH /{connectionId}/MailSubscription/$subscriptions/{subscriptionId}`

```json
{
  "request": {
    "method": "PATCH",
    "path": "/MailSubscription/$subscriptions/{subscriptionId}",
    "queries": {
      "options": "<base64 options token from create response>"
    },
    "body": {
      "NotificationUrl": "https://your-callback-url"
    }
  }
}
```

**Important:** The body **must** include `NotificationUrl`. An empty body returns `500 Internal Server Error`.

**Response (200 OK):**

```json
{
  "id": "82f94813-bcdb-4b1b-b576-6b8912dbb951",
  "notificationType": "webhook",
  "notificationUrl": "https://your-callback-url",
  "renewInterval": "PT1H",
  "resource": "..."
}
```

---

## 7. Deleting a Subscription

**Connector endpoint:** `DELETE /{connectionId}/MailSubscription/$subscriptions/{subscriptionId}`

```json
{
  "request": {
    "method": "DELETE",
    "path": "/MailSubscription/$subscriptions/{subscriptionId}",
    "queries": {
      "options": "<base64 options token from create response>"
    }
  }
}
```

**Response:** `200 OK` with empty body.

---

## Quick Reference

| Property | Value |
|----------|-------|
| **Subscription type** | Graph-based push webhook (poke) |
| **Renew interval** | Fixed at 1 hour (`PT1H`) — not configurable |
| **Notification payload** | Empty body (poke only) |
| **Auth required** | ARM token (for dynamic invoke) + authenticated Office 365 connection |
| **Filter options** | `folderPath`, `importance`, `fetchOnlyWithAttachment` |
| **State to persist** | `subscriptionId` + `optionsToken` (for renew/delete) + `LastPollInformation` cursor (for fetching) |
| **Alternatives** | `MailSubscriptionPoke` (Outlook-based, older), `MailSubscription/$subscriptions` (polling/batch) |

## End-to-End Flow

```
1. INITIALIZE cursor — call GET /Mail/OnNewEmail (no cursor) → save cursor from Location header
2. CREATE subscription → save subscriptionId + optionsToken
3. Handle VALIDATION → echo back validationToken as text/plain
4. Receive POKE (POST, empty body) → new email arrived
5. FETCH new emails — call GET /Mail/OnNewEmail?LastPollInformation={cursor}
   → 200 OK: process emails, save new cursor from Location header
   → 202 Accepted: nothing new (duplicate poke), save cursor anyway
6. RENEW subscription every ~50 min via PATCH (requires NotificationUrl + optionsToken)
7. DELETE subscription when done
```
