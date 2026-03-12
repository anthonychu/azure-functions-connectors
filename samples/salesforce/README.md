# Sample: Salesforce Triggers & Client

This sample demonstrates Salesforce triggers (new Contact, updated Opportunity) and typed client usage.

## Prerequisites

- Python 3.10+
- Azure Functions Core Tools v4
- An Azure API Connection for Salesforce (authenticated via OAuth)
- A managed identity or service principal with `Microsoft.Web/connections/dynamicInvoke/action` on the connection

## Setup

1. Copy `local.settings.json.template` to `local.settings.json`
2. Fill in your Salesforce connection resource ID
3. Install dependencies: `pip install -r requirements.txt`
4. Run: `func start`
