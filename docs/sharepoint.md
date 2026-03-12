# SharePoint Online Connector API Documentation

## Table of Contents

- [Overview](#overview)
- [Finding Your IDs](#finding-your-ids)
- [Important URL Encoding Note](#important-url-encoding-note)
- [Triggers](#triggers)
  - [new_item_trigger](#new_item_trigger)
  - [updated_item_trigger](#updated_item_trigger)
  - [new_file_trigger](#new_file_trigger)
  - [updated_file_trigger](#updated_file_trigger)
- [Models](#models)
  - [SharePointItem](#sharepointitem)
  - [SharePointFile](#sharepointfile)
- [Client](#client)
  - [Sites and Lists](#sites-and-lists)
  - [List Items](#list-items)
  - [Files and Folders](#files-and-folders)
  - [HTTP Request (escape hatch)](#http-request-escape-hatch)

## Overview

The SharePoint Online connector provides:

- **Trigger decorators** via `SharePointTriggers` for polling list item and file changes.
- A typed **action client** (`SharePointClient`) for site/list/item/file operations.
- Typed trigger models:
  - `SharePointItem`
  - `SharePointFile`

Get a client from triggers:

```python
sp = connectors.sharepoint.get_client(connection_id="sharepoint-conn")
```

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

Store it as an app setting (e.g., `SHAREPOINT_CONNECTION_ID`) and reference it with `%SHAREPOINT_CONNECTION_ID%` in your trigger decorators.

### Site URL

The `site_url` is the full URL of your SharePoint site, e.g.:
- `https://contoso.sharepoint.com/sites/MySite`
- `https://contoso.sharepoint.com/teams/Engineering`

Find it by opening your SharePoint site in a browser — the URL in the address bar up to the site name.

### List ID

Lists are identified by their GUID. Use the client to discover list IDs:

```python
client = connectors.sharepoint.get_client("%SHAREPOINT_CONNECTION_ID%")

# List all lists/libraries on a site
lists = await client.get_all_lists(site_url="%SHAREPOINT_SITE_URL%")
for lst in lists.get("value", []):
    print(f"{lst.get('DisplayName')}: {lst.get('Name')}")
```

List IDs look like: `52b22385-2fbe-482c-9095-0d2611b0064e`


## Important: Site URL Encoding

SharePoint site URLs require special encoding internally. **The SDK handles this automatically** — just pass the plain site URL (e.g., `https://contoso.sharepoint.com/sites/MySite`) or an env var reference (e.g., `%SHAREPOINT_SITE_URL%`). No manual encoding needed.

## Triggers

Trigger decorators are created from `connectors.sharepoint`.
All trigger methods accept optional `min_interval` (default: 60) and `max_interval` (default: 300) parameters to control polling frequency in seconds.

### `new_item_trigger(connection_id: str, site_url: str, list_id: str) -> Callable`

Fires when new items are created in a SharePoint list.

```python
@connectors.sharepoint.new_item_trigger(
    connection_id="%SHAREPOINT_CONNECTION_ID%",
    site_url="%SHAREPOINT_SITE_URL%",
    list_id="%SHAREPOINT_LIST_ID%",
)
async def on_new_item(item: SharePointItem):
    print(item.id, item.title)
```

### `updated_item_trigger(connection_id: str, site_url: str, list_id: str) -> Callable`

Fires when items are updated in a SharePoint list.

```python
@connectors.sharepoint.updated_item_trigger(
    connection_id="%SHAREPOINT_CONNECTION_ID%",
    site_url="%SHAREPOINT_SITE_URL%",
    list_id="%SHAREPOINT_LIST_ID%",
)
async def on_updated_item(item: SharePointItem):
    print(item.id, item.modified)
```

### `new_file_trigger(connection_id: str, site_url: str, library_id: str) -> Callable`

Fires when new files are added to a SharePoint document library.

```python
@connectors.sharepoint.new_file_trigger(
    connection_id="%SHAREPOINT_CONNECTION_ID%",
    site_url="%SHAREPOINT_SITE_URL%",
    library_id="%SHAREPOINT_LIBRARY_ID%",
)
async def on_new_file(file_item: SharePointFile):
    print(file_item.name, file_item.path)
```

### `updated_file_trigger(connection_id: str, site_url: str, library_id: str) -> Callable`

Fires when files are updated in a SharePoint document library.

```python
@connectors.sharepoint.updated_file_trigger(
    connection_id="%SHAREPOINT_CONNECTION_ID%",
    site_url="%SHAREPOINT_SITE_URL%",
    library_id="%SHAREPOINT_LIBRARY_ID%",
)
async def on_updated_file(file_item: SharePointFile):
    print(file_item.name, file_item.modified)
```

## Models

### `SharePointItem`

Typed wrapper for SharePoint list-item trigger payloads.

| Property | Type | Description |
|----------|------|-------------|
| `id` | `str` | Item ID from `ID`, `Id`, or `id`. |
| `title` | `str` | Item title from `Title` or `title`. |
| `created` | `str` | Created timestamp from `Created` or `created`. |
| `modified` | `str` | Modified timestamp from `Modified` or `modified`. |
| `author` | `str` | Author display name/value from `Author`. |
| `editor` | `str` | Editor display name/value from `Editor`. |
| `etag` | `str` | ETag from `@odata.etag` or `OData__x0040_odata_x002e_etag`. |
| `internal_id` | `str` | Internal item ID from `ItemInternalId`. |

### `SharePointFile`

Extends `SharePointItem` with file-specific fields.

| Property | Type | Description |
|----------|------|-------------|
| `name` | `str` | File name from `{Name}` or `FileLeafRef`. |
| `path` | `str` | File path from `{Path}`, `FileDirRef`, or `FileRef`. |
| `size` | `str \| int` | File size from `{FileSizeDisplay}` or `File_x0020_Size`. |
| `content_type` | `str` | Content type from `{ContentType}` or `ContentType`. |

## Client

Create a typed client:

```python
client = connectors.sharepoint.get_client("%SHAREPOINT_CONNECTION_ID%")
```

### Sites and Lists

### `get_sites()`
```python
sites = await client.get_sites()
```

### `get_lists(site_url: str)`
```python
lists = await client.get_lists(site_url="%SHAREPOINT_SITE_URL%")
```

### `get_all_lists(site_url: str)`
```python
all_lists = await client.get_all_lists(site_url="%SHAREPOINT_SITE_URL%")
```

### List Items

### `get_items(site_url: str, list_id: str, filter: str | None = None, orderby: str | None = None, top: int | None = None)`
```python
items = await client.get_items(
    site_url="%SHAREPOINT_SITE_URL%",
    list_id="%SHAREPOINT_LIST_ID%",
    top=25,
)
```

### `get_item(site_url: str, list_id: str, item_id: str)`
```python
item = await client.get_item(
    site_url="%SHAREPOINT_SITE_URL%",
    list_id="%SHAREPOINT_LIST_ID%",
    item_id="42",
)
```

### `create_item(site_url: str, list_id: str, item: dict)`
```python
created = await client.create_item(
    site_url="%SHAREPOINT_SITE_URL%",
    list_id="%SHAREPOINT_LIST_ID%",
    item={"Title": "New item"},
)
```

### `update_item(site_url: str, list_id: str, item_id: str, updates: dict)`
```python
updated = await client.update_item(
    site_url="%SHAREPOINT_SITE_URL%",
    list_id="%SHAREPOINT_LIST_ID%",
    item_id="42",
    updates={"Title": "Updated title"},
)
```

### `delete_item(site_url: str, list_id: str, item_id: str)`
```python
await client.delete_item(
    site_url="%SHAREPOINT_SITE_URL%",
    list_id="%SHAREPOINT_LIST_ID%",
    item_id="42",
)
```

### Files and Folders

### `get_files(site_url: str, library_id: str, folder_path: str | None = None)`
```python
files = await client.get_files(
    site_url="%SHAREPOINT_SITE_URL%",
    library_id="%SHAREPOINT_LIBRARY_ID%",
    folder_path="/Shared Documents/General",
)
```

### `get_file_content(site_url: str, file_id: str)`
```python
content = await client.get_file_content(
    site_url="%SHAREPOINT_SITE_URL%",
    file_id="<file-id>",
)
```

### `create_file(site_url: str, folder_path: str, file_name: str, content: str)`
```python
created = await client.create_file(
    site_url="%SHAREPOINT_SITE_URL%",
    folder_path="/Shared Documents/General",
    file_name="hello.txt",
    content="Hello, SharePoint!",
)
```

### `list_folder(site_url: str, folder_id: str)`
```python
folder_items = await client.list_folder(
    site_url="%SHAREPOINT_SITE_URL%",
    folder_id="<folder-id>",
)
```

### `list_root_folder(site_url: str)`
```python
root = await client.list_root_folder(site_url="%SHAREPOINT_SITE_URL%")
```

### `create_folder(site_url: str, list_id: str, path: str)`
```python
new_folder = await client.create_folder(
    site_url="%SHAREPOINT_SITE_URL%",
    list_id="%SHAREPOINT_LIBRARY_ID%",
    path="Shared Documents/New Folder",
)
```

### HTTP Request (escape hatch)

### `http_request(site_url: str, method: str, uri: str, body: dict | None = None)`
```python
raw = await client.http_request(
    site_url="%SHAREPOINT_SITE_URL%",
    method="GET",
    uri="_api/web/lists",
)
```
