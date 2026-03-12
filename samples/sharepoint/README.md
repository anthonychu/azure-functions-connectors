# Sample: SharePoint Online Triggers & Client

This sample demonstrates SharePoint Online triggers (new list items, updated files) and typed client usage.

## Prerequisites

- Python 3.10+
- Azure Functions Core Tools v4
- An Azure API Connection for SharePoint Online (authenticated)
- A managed identity or service principal with `Microsoft.Web/connections/dynamicInvoke/action` on the connection

## Setup

1. Copy `local.settings.json.template` to `local.settings.json`
2. Fill in your SharePoint connection and resource values
3. Install dependencies: `pip install -r requirements.txt`
4. Run: `func start`

## Notes

- Use the full site URL (for example, `https://contoso.sharepoint.com/sites/MySite`) in `SHAREPOINT_SITE_URL`.
- The SDK automatically applies SharePoint's required double-encoding for dynamicInvoke paths.
