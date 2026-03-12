# Salesforce Connector API Documentation

## Table of Contents

- [Overview](#overview)
- [Finding Your IDs](#finding-your-ids)
- [Triggers](#triggers)
  - [new_item_trigger](#new_item_trigger)
  - [updated_item_trigger](#updated_item_trigger)
  - [deleted_item_trigger](#deleted_item_trigger)
- [Models](#models)
  - [SalesforceRecord](#salesforcerecord)
- [Client](#client)
  - [Records (CRUD)](#records-crud)
  - [Convenience object methods](#convenience-object-methods)
  - [Query](#query)
  - [Bulk](#bulk)
  - [Utility](#utility)

## Overview

The Salesforce connector provides:

- **Trigger decorators** via `SalesforceTriggers` for batch polling on records.
- A typed **action client** (`SalesforceClient`) for table/record operations.
- A typed trigger model (`SalesforceRecord`) with common Salesforce fields.

Get a client from triggers:

```python
sf = connectors.salesforce.get_client(connection_id="salesforce-conn")
```

---

## Finding Your IDs

### Connection ID

The `connection_id` is the full ARM resource ID of your API Connection in Azure:

```
/subscriptions/{subscription-id}/resourceGroups/{resource-group}/providers/Microsoft.Web/connections/{connection-name}
```

To find it:
1. Open the [Azure Portal](https://portal.azure.com)
2. Navigate to your resource group
3. Find your API Connection resource
4. The resource ID is in the **Properties** blade, or construct it from your subscription ID, resource group name, and connection name

Alternatively, use the CLI:
```bash
az resource list --resource-group {rg} --resource-type Microsoft.Web/connections --query "[].id" -o tsv
```

Store it as an app setting (e.g., `SALESFORCE_CONNECTION_ID`) and reference it with `%SALESFORCE_CONNECTION_ID%` in your trigger decorators.

### Table (Object) Name

The `table` parameter is the Salesforce API name of the object:
- Standard objects: `account`, `contact`, `lead`, `opportunity`, `case`
- Custom objects: use the API name (e.g., `Custom_Object__c`)

Use the client to discover available tables:

```python
client = connectors.salesforce.get_client("%SALESFORCE_CONNECTION_ID%")
tables = await client.get_tables()
for t in tables.get("value", []):
    print(f"{t.get('DisplayName')}: {t.get('Name')}")
```


## Triggers

Trigger decorators are created from `connectors.salesforce`.
All trigger methods accept optional `min_interval` (default: 60) and `max_interval` (default: 300) parameters to control polling frequency in seconds.

### `new_item_trigger(connection_id: str, table: str, filter: str | None = None, orderby: str | None = None, select: str | None = None) -> Callable`

Fires when new records are created for a Salesforce object.

```python
@connectors.salesforce.new_item_trigger(
    connection_id="%SALESFORCE_CONNECTION_ID%",
    table="contact",
    filter="Name ne null",
)
async def on_new_contact(item: SalesforceRecord):
    print(item.id, item.name)
```

### `updated_item_trigger(connection_id: str, table: str, filter: str | None = None, orderby: str | None = None, select: str | None = None) -> Callable`

Fires when records are updated for a Salesforce object.

```python
@connectors.salesforce.updated_item_trigger(
    connection_id="%SALESFORCE_CONNECTION_ID%",
    table="opportunity",
    orderby="LastModifiedDate desc",
)
async def on_updated_opportunity(item: SalesforceRecord):
    print(item.id, item.last_modified_date)
```

### `deleted_item_trigger(connection_id: str, table: str, filter: str | None = None, orderby: str | None = None, top: int | None = None) -> Callable`

Fires when records are deleted for a Salesforce object.

```python
@connectors.salesforce.deleted_item_trigger(
    connection_id="%SALESFORCE_CONNECTION_ID%",
    table="lead",
    top=50,
)
async def on_deleted_lead(item: SalesforceRecord):
    print(item.id)
```

---

## Models

### `SalesforceRecord`

Typed wrapper for trigger payload records.

| Property | Type | Description |
|----------|------|-------------|
| `id` | `str` | Record ID (`Id` or `id`). |
| `name` | `str` | Record name (`Name` or `name`). |
| `record_type` | `str` | Object type from `attributes.type`. |
| `created_date` | `str` | Created timestamp (`CreatedDate` or `createdDate`). |
| `last_modified_date` | `str` | Last-modified timestamp (`LastModifiedDate` or `lastModifiedDate`). |
| `owner_id` | `str` | Owner ID (`OwnerId` or `ownerId`). |

Example:

```python
def inspect_record(record: SalesforceRecord):
    print(record.id, record.name, record.record_type)
```

---

## Client

Create a typed client:

```python
client = connectors.salesforce.get_client("%SALESFORCE_CONNECTION_ID%")
```

### Records (CRUD)

### `get_records(table: str, filter: str | None = None, orderby: str | None = None, select: str | None = None, top: int | None = None)`
```python
records = await client.get_records(
    "contact",
    filter="Name ne null",
    orderby="CreatedDate desc",
    select="Id,Name,OwnerId",
    top=25,
)
```

### `get_record(table: str, record_id: str)`
```python
record = await client.get_record("contact", "003XXXXXXXXXXXX")
```

### `create_record(table: str, record: dict)`
```python
created = await client.create_record("lead", {"LastName": "Doe", "Company": "Contoso"})
```

### `update_record(table: str, record_id: str, updates: dict)`
```python
updated = await client.update_record("account", "001XXXXXXXXXXXX", {"Name": "Contoso Ltd"})
```

### `delete_record(table: str, record_id: str)`
```python
await client.delete_record("case", "500XXXXXXXXXXXX")
```

### Convenience object methods

### `get_accounts(filter: str | None = None)`
```python
accounts = await client.get_accounts(filter="Name ne null")
```

### `get_contacts(filter: str | None = None)`
```python
contacts = await client.get_contacts(filter="Name ne null")
```

### `get_leads(filter: str | None = None)`
```python
leads = await client.get_leads(filter="Company ne null")
```

### `get_opportunities(filter: str | None = None)`
```python
opps = await client.get_opportunities(filter="Name ne null")
```

### `get_cases(filter: str | None = None)`
```python
cases = await client.get_cases(filter="Status ne null")
```

### Query

### `execute_soql(query: str)`
```python
result = await client.execute_soql(
    "SELECT Id, Name FROM Contact ORDER BY CreatedDate DESC LIMIT 10"
)
```

### Bulk

### `create_bulk_job(table: str, operation: str, content_type: str = "CSV")`
```python
job = await client.create_bulk_job(table="contact", operation="insert")
```

### Utility

### `get_tables()`
```python
tables = await client.get_tables()
```

### `get_table_metadata(table: str)`
```python
metadata = await client.get_table_metadata("contact")
```

### `http_request(method: str, url: str, body: dict | None = None)`
```python
raw = await client.http_request(
    method="GET",
    url="/services/data/v58.0/sobjects/Contact/describe",
)
```
