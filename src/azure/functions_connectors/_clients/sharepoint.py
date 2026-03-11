"""Typed SharePoint Online client for calling connector actions."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote

from .._env import resolve_value

if TYPE_CHECKING:
    from .._client import ConnectorClient


def _double_encode(url: str) -> str:
    return quote(quote(resolve_value(url), safe=""), safe="")


class SharePointClient:
    """Typed client for SharePoint Online connector actions."""

    def __init__(self, client: ConnectorClient) -> None:
        self._client = client

    async def get_sites(self) -> dict:
        """List available SharePoint sites for this connection."""
        return await self._client.invoke("GET", "/datasets")

    async def get_lists(self, site_url: str) -> dict:
        """List SharePoint lists for a site."""
        encoded_site = _double_encode(site_url)
        return await self._client.invoke("GET", f"/datasets/{encoded_site}/tables")

    async def get_all_lists(self, site_url: str) -> dict:
        """List all SharePoint lists/libraries for a site."""
        encoded_site = _double_encode(site_url)
        return await self._client.invoke("GET", f"/datasets/{encoded_site}/alltables")

    async def get_items(
        self,
        site_url: str,
        list_id: str,
        filter: str | None = None,
        orderby: str | None = None,
        top: int | None = None,
    ) -> dict:
        """Get items from a SharePoint list."""
        encoded_site = _double_encode(site_url)
        resolved_list_id = resolve_value(list_id)
        queries: dict[str, str] = {}
        if filter is not None:
            queries["$filter"] = filter
        if orderby is not None:
            queries["$orderby"] = orderby
        if top is not None:
            queries["$top"] = str(top)
        return await self._client.invoke(
            "GET",
            f"/datasets/{encoded_site}/tables/{resolved_list_id}/items",
            queries=queries or None,
        )

    async def get_item(self, site_url: str, list_id: str, item_id: str) -> dict:
        """Get a single SharePoint list item by ID."""
        encoded_site = _double_encode(site_url)
        resolved_list_id = resolve_value(list_id)
        resolved_item_id = resolve_value(item_id)
        return await self._client.invoke(
            "GET",
            f"/datasets/{encoded_site}/tables/{resolved_list_id}/items/{resolved_item_id}",
        )

    async def create_item(self, site_url: str, list_id: str, item: dict) -> dict:
        """Create a SharePoint list item."""
        encoded_site = _double_encode(site_url)
        resolved_list_id = resolve_value(list_id)
        return await self._client.invoke(
            "POST",
            f"/datasets/{encoded_site}/tables/{resolved_list_id}/items",
            body=item,
        )

    async def update_item(
        self,
        site_url: str,
        list_id: str,
        item_id: str,
        updates: dict,
    ) -> dict:
        """Update a SharePoint list item."""
        encoded_site = _double_encode(site_url)
        resolved_list_id = resolve_value(list_id)
        resolved_item_id = resolve_value(item_id)
        return await self._client.invoke(
            "PATCH",
            f"/datasets/{encoded_site}/tables/{resolved_list_id}/items/{resolved_item_id}",
            body=updates,
        )

    async def delete_item(self, site_url: str, list_id: str, item_id: str) -> dict:
        """Delete a SharePoint list item."""
        encoded_site = _double_encode(site_url)
        resolved_list_id = resolve_value(list_id)
        resolved_item_id = resolve_value(item_id)
        return await self._client.invoke(
            "DELETE",
            f"/datasets/{encoded_site}/tables/{resolved_list_id}/items/{resolved_item_id}",
        )

    async def get_files(
        self,
        site_url: str,
        library_id: str,
        folder_path: str | None = None,
    ) -> dict:
        """Get files from a SharePoint document library."""
        encoded_site = _double_encode(site_url)
        resolved_library_id = resolve_value(library_id)
        queries: dict[str, str] = {}
        if folder_path is not None:
            resolved_folder_path = resolve_value(folder_path).replace("'", "''")
            queries["$filter"] = f"FileDirRef eq '{resolved_folder_path}'"
        return await self._client.invoke(
            "GET",
            f"/datasets/{encoded_site}/tables/{resolved_library_id}/getfileitems",
            queries=queries or None,
        )

    async def get_file_content(self, site_url: str, file_id: str) -> dict:
        """Get content for a SharePoint file."""
        encoded_site = _double_encode(site_url)
        resolved_file_id = resolve_value(file_id)
        return await self._client.invoke(
            "GET",
            f"/datasets/{encoded_site}/files/{resolved_file_id}/content",
        )

    async def create_file(
        self,
        site_url: str,
        folder_path: str,
        file_name: str,
        content: str,
    ) -> dict:
        """Create a file in SharePoint."""
        encoded_site = _double_encode(site_url)
        return await self._client.invoke(
            "POST",
            f"/datasets/{encoded_site}/files",
            queries={
                "folderPath": resolve_value(folder_path),
                "name": resolve_value(file_name),
            },
            body=content,
        )

    async def list_folder(self, site_url: str, folder_id: str) -> dict:
        """List files and folders within a SharePoint folder."""
        encoded_site = _double_encode(site_url)
        resolved_folder_id = resolve_value(folder_id)
        return await self._client.invoke(
            "GET",
            f"/datasets/{encoded_site}/folders/{resolved_folder_id}",
        )

    async def list_root_folder(self, site_url: str) -> dict:
        """List the root folder for a SharePoint site/library context."""
        encoded_site = _double_encode(site_url)
        return await self._client.invoke("GET", f"/datasets/{encoded_site}/folders")

    async def create_folder(self, site_url: str, list_id: str, path: str) -> dict:
        """Create a new folder in a SharePoint list/library."""
        encoded_site = _double_encode(site_url)
        resolved_list_id = resolve_value(list_id)
        return await self._client.invoke(
            "POST",
            f"/datasets/{encoded_site}/tables/{resolved_list_id}/newFolder",
            body={"path": resolve_value(path)},
        )

    async def http_request(
        self,
        site_url: str,
        method: str,
        uri: str,
        body: dict | None = None,
    ) -> dict:
        """Send a raw SharePoint HTTP request via connector proxy."""
        encoded_site = _double_encode(site_url)
        return await self._client.invoke(
            "POST",
            f"/datasets/{encoded_site}/httprequest",
            queries={
                "Method": resolve_value(method),
                "Uri": resolve_value(uri),
            },
            body=body,
        )
