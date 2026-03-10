# Graph HTTP Request Proxy — Limitation

## Summary

Both Office 365 and Teams connectors include a "Send an HTTP request" action
that proxies requests to Microsoft Graph. However, this action **does not work
via dynamicInvoke** (the ARM API we use for all connector operations).

## The Problem

The `Method` and `Uri` parameters are defined as **headers** in the connector
swagger. The `dynamicInvoke` API does not properly forward these headers to the
connector action. Every call returns:

```
{"error": {"code": 400, "message": "Empty Http Method provided."}}
```

Tested with:
- Office 365: `POST /codeless/httprequest`
- Teams: `POST /httprequest`
- Passing Method/Uri in queries, headers, and body — all fail

## Impact

- Cannot use Graph HTTP proxy through `ConnectorClient.invoke()`
- Cannot poll for data not covered by named connector endpoints (e.g., chat messages, reactions)
- This action works in Logic Apps/Power Automate where the runtime handles header passing correctly

## Workaround

For scenarios that need raw Graph access, use the Microsoft Graph SDK directly
with its own authentication (e.g., `azure-identity` + `msgraph-sdk-python`),
bypassing the connector entirely.
