# Setup & Production Guide

This guide walks through creating and using Azure managed API connections with `azure-functions-connectors`, including Office 365 OAuth setup, RBAC, local development, and production deployment.

## 1. Creating an API Connection

API Connections are ARM resources that store credentials for managed connectors. They cannot be created directly in the Azure Portal — use the CLI or an ARM template.

Connection resources are ARM resources at:

`/subscriptions/{subId}/resourceGroups/{rg}/providers/Microsoft.Web/connections/{name}`

### Using Azure CLI

```bash
# Create the connection
az rest --method PUT \
  --url "https://management.azure.com/subscriptions/{subId}/resourceGroups/{rg}/providers/Microsoft.Web/connections/{connectionName}?api-version=2016-06-01" \
  --body '{
    "location": "westus",
    "properties": {
      "api": {
        "id": "/subscriptions/{subId}/providers/Microsoft.Web/locations/westus/managedApis/office365"
      },
      "displayName": "Office 365",
      "parameterValues": {}
    }
  }'
```

Replace `office365` with the connector API name (e.g., `teams`, `salesforce`, `sharepointonline`). To list available connectors:

```bash
az rest --method GET \
  --url "https://management.azure.com/subscriptions/{subId}/providers/Microsoft.Web/locations/{location}/managedApis?api-version=2016-06-01" \
  --query "value[].{name:name, displayName:properties.displayName}" -o table
```

### Using Bicep / ARM Template

```bicep
resource connection 'Microsoft.Web/connections@2016-06-01' = {
  name: 'office365'
  location: resourceGroup().location
  properties: {
    api: {
      id: subscriptionResourceId('Microsoft.Web/locations/managedApis', resourceGroup().location, 'office365')
    }
    displayName: 'Office 365'
    parameterValues: {}
  }
}
```

## 2. Finding Connection IDs

Every connector trigger/client uses a `connection_id` that points to your API Connection ARM resource:

```
/subscriptions/{subscription-id}/resourceGroups/{resource-group}/providers/Microsoft.Web/connections/{connection-name}
```

You can find this in Azure Portal:
1. Open the [Azure Portal](https://portal.azure.com)
2. Go to your resource group
3. Open the API Connection resource
4. Copy the **Resource ID** from the **Properties** blade

Or use Azure CLI:

```bash
az resource list --resource-group {rg} --resource-type Microsoft.Web/connections --query "[].id" -o tsv
```

Store the value in Function App settings (for example, `OFFICE365_CONNECTION_ID`) and reference it in code with `%OFFICE365_CONNECTION_ID%`.

## 3. Authenticating the Connection

OAuth connectors (like Office 365) require user consent after creation. The connection starts in an **Unauthenticated** state.

### Using Azure Portal

1. Navigate to your resource group
2. Open the API Connection resource
3. Click **Edit API Connection** → **Authorize** → sign in → **Save**

### Using CLI (Consent Link)

```bash
# Get your Azure AD Object ID
OBJECT_ID=$(az ad signed-in-user show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)

# Get consent link
az rest --method POST \
  --url "https://management.azure.com/subscriptions/{subId}/resourceGroups/{rg}/providers/Microsoft.Web/connections/{connectionName}/listConsentLinks?api-version=2016-06-01" \
  --body "{\"parameters\": [{\"objectId\": \"$OBJECT_ID\", \"tenantId\": \"$TENANT_ID\", \"parameterName\": \"token\", \"redirectUrl\": \"https://portal.azure.com\"}]}"
```

Open the returned `link` URL in a browser, sign in, and the connection will be authenticated.

The connection stores the OAuth token and is **per-user**.

## 4. RBAC — Granting Your Function App Access

Your Function App managed identity needs permission to invoke actions on the connection.

### Option A: Custom Role (Recommended — Least Privilege)

```json
{
  "Name": "API Connection Invoker",
  "Description": "Allows invoking actions on API connections",
  "Actions": [
    "Microsoft.Web/connections/dynamicInvoke/action",
    "Microsoft.Web/connections/read"
  ],
  "AssignableScopes": ["/subscriptions/{subId}/resourceGroups/{rg}"]
}
```

```bash
az role definition create --role-definition role.json
az role assignment create \
  --assignee <function-app-managed-identity-object-id> \
  --role "API Connection Invoker" \
  --scope "/subscriptions/{subId}/resourceGroups/{rg}/providers/Microsoft.Web/connections/{name}"
```

### Option B: Built-in Role

Logic App Contributor scoped to the connection resource:

```bash
az role assignment create \
  --assignee <managed-identity-object-id> \
  --role "Logic App Contributor" \
  --scope "/subscriptions/{subId}/resourceGroups/{rg}/providers/Microsoft.Web/connections/{name}"
```

**Warning:** If scoped to a resource group that also contains a Function App + Storage Account, Logic App Contributor grants `storageAccounts/listkeys` access. Use the custom role instead.

## 5. App Settings

| Setting | Required | Description |
|---------|----------|-------------|
| `AzureWebJobsStorage` | Yes | Storage account connection string (for blob state + queues). Already required by Azure Functions. |
| `OFFICE365_CONNECTION_ID` | Yes (for Office 365) | Full ARM resource ID of the API connection, e.g., `/subscriptions/.../connections/office365` |

For local development:

- `AzureWebJobsStorage` can be set to Azurite:
  `UseDevelopmentStorage=true`
- Run Azurite via Docker:
  `docker run -d --rm --name azurite -p 10000:10000 -p 10001:10001 -p 10002:10002 mcr.microsoft.com/azure-storage/azurite azurite --skipApiVersionCheck --blobHost 0.0.0.0 --queueHost 0.0.0.0 --tableHost 0.0.0.0`

## 6. Local Development

```bash
# 1. Start Azurite
docker run -d --rm --name azurite \
  -p 10000:10000 -p 10001:10001 -p 10002:10002 \
  mcr.microsoft.com/azure-storage/azurite \
  azurite --skipApiVersionCheck --blobHost 0.0.0.0 --queueHost 0.0.0.0 --tableHost 0.0.0.0

# 2. Create venv and install (use any Python version supported by Azure Functions)
cd samples/office365
python3 -m venv .venv && source .venv/bin/activate
pip install -e ../../ aiohttp

# 3. Copy and edit local settings
cp local.settings.json.template local.settings.json
# Edit: set OFFICE365_CONNECTION_ID

# 4. Run
func start
```

For local development, you still need a real Azure API Connection (created in Azure Portal). The connection stores the OAuth token — Azurite is only used for the package's internal blob/queue storage.

## 7. Production Deployment

### Deploy the Function App

Use standard Azure Functions deployment. Install the package from `requirements.txt`:

```txt
azure-functions-connectors @ https://github.com/anthonychu/azure-functions-connectors-python/releases/download/v0.1.0b1/azure_functions_connectors-0.1.0b1-py3-none-any.whl
```

> **Tip:** Check the [Releases page](https://github.com/anthonychu/azure-functions-connectors-python/releases) for the latest version URL.

### Enable Managed Identity

```bash
az functionapp identity assign --name <app-name> --resource-group <rg>
```

### Grant RBAC (see section 4)

### App Settings

Set `OFFICE365_CONNECTION_ID` (or equivalent) in the Function App's Application Settings.

`AzureWebJobsStorage` is already configured by Azure Functions.

### Scaling Considerations

- Polling is centralized (one instance polls at a time)
- Item processing scales out automatically
- Polling interval defaults to 1 minute (configurable)
- Trigger state survives restarts and deployments

## 8. Known Limitations

- **Teams triggers:** support top-level channel posts and @mentions only. Replies within threads and chat message triggers are not currently available.
- **`http_request()` actions:** the raw HTTP request method on Office 365, Teams, and SharePoint connectors is not currently supported. Use the typed client methods or the Microsoft Graph SDK instead.
- **SharePoint site URLs:** the typed `connectors.sharepoint.*` helpers handle encoding automatically, but generic trigger/client paths require manual encoding.

## 9. Available Connectors

Any Azure managed API connector can be used with `generic_trigger()` and `get_client()`. Popular options:

| Connector | API Name | Use Case |
|-----------|----------|----------|
| Office 365 Outlook | `office365` | Email, Calendar, Contacts |
| Salesforce | `salesforce` | CRM records |
| SharePoint Online | `sharepointonline` | Lists, Documents |
| Microsoft Teams | `teams` | Messages, Channels, Triggers |
| Dynamics 365 | `dynamicscrmonline` | Business data |
| OneDrive for Business | `onedriveforbusiness` | Files |
| Azure Key Vault | `keyvault` | Secrets |
| SQL Server | `sql` | Database |

To discover connectors:

```bash
az rest --method GET \
  --url "https://management.azure.com/subscriptions/{subId}/providers/Microsoft.Web/locations/{location}/managedApis?api-version=2016-06-01" \
  --query "value[].name" -o tsv
```
