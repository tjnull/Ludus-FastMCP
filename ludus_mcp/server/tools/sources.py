"""Content source FastMCP tools for Ludus MCP server (Ludus 2.0+ only).

Sources are git repos or uploaded archives that publish blueprints, packer
templates, Ansible roles and collections. They are how additional templates
(rocky, ubuntu, remnux, flare-vm, commando-vm, ...) and prebuilt labs such as
GOAD get onto a Ludus server.
"""

from typing import Any
from fastmcp import FastMCP
from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.server.tools.utils import format_tool_response
from ludus_mcp.utils.version_guard import require_v2


def create_source_tools(client: LudusAPIClient) -> FastMCP:
    """Create content source tools.

    Args:
        client: Ludus API client

    Returns:
        FastMCP instance with source tools registered
    """
    mcp = FastMCP("Content Sources")

    @mcp.tool()
    async def list_sources() -> list | dict:
        """List content sources configured on the Ludus server.

        Returns:
            Sources with their sourceID, type, url and last sync status
        """
        guard = await require_v2(client, "Content sources")
        if guard:
            return guard
        return format_tool_response(await client.list_sources())

    @mcp.tool()
    async def get_source(source_id: str) -> dict:
        """Get details for a single content source.

        Args:
            source_id: Source ID (e.g. "ludus-source-bsl")
        """
        guard = await require_v2(client, "Content sources")
        if guard:
            return guard
        return format_tool_response(await client.get_source(source_id))

    @mcp.tool()
    async def get_source_catalog(source_id: str) -> dict:
        """Get everything a source publishes, with install state for each item.

        This is the tool to use when asked what templates, blueprints or roles
        are available to add to the server.

        Args:
            source_id: Source ID (e.g. "ludus-source-bsl")

        Returns:
            Catalog with blueprints, templates, roles and collections
        """
        guard = await require_v2(client, "Content sources")
        if guard:
            return guard
        return format_tool_response(await client.get_source_catalog(source_id))

    @mcp.tool()
    async def list_source_templates(source_id: str) -> list | dict:
        """List packer templates published by a source.

        Args:
            source_id: Source ID
        """
        guard = await require_v2(client, "Content sources")
        if guard:
            return guard
        return format_tool_response(await client.list_source_templates(source_id))

    @mcp.tool()
    async def list_source_blueprints(source_id: str) -> list | dict:
        """List blueprints published by a source (GOAD, AD + Elastic, ...).

        Args:
            source_id: Source ID
        """
        guard = await require_v2(client, "Content sources")
        if guard:
            return guard
        return format_tool_response(await client.list_source_blueprints(source_id))

    @mcp.tool()
    async def list_source_roles(source_id: str) -> list | dict:
        """List Ansible roles published by a source.

        Args:
            source_id: Source ID
        """
        guard = await require_v2(client, "Content sources")
        if guard:
            return guard
        return format_tool_response(await client.list_source_roles(source_id))

    @mcp.tool()
    async def list_source_collections(source_id: str) -> list | dict:
        """List Ansible collections published by a source.

        Args:
            source_id: Source ID
        """
        guard = await require_v2(client, "Content sources")
        if guard:
            return guard
        return format_tool_response(await client.list_source_collections(source_id))

    @mcp.tool()
    async def install_from_source(
        source_id: str,
        templates: list[str] | None = None,
        blueprints: list[str] | None = None,
        roles: list[str] | None = None,
        collections: list[str] | None = None,
        install_globally: bool = False,
        force: bool = False,
        no_deps: bool = False,
    ) -> dict:
        """Install templates, blueprints, roles or collections from a source.

        Installing a template makes its packer definition available; it still
        has to be built with build_template afterwards.

        IMPORTANT: the selection REPLACES the source's previous selection, so
        pass every item you want installed in one call, not one call per item.

        Args:
            source_id: Source to install from
            templates: Packer template names (see list_source_templates)
            blueprints: Blueprint IDs (see list_source_blueprints)
            roles: Source-bundled Ansible role names
            collections: Source-bundled collection FQCNs (namespace.name)
            install_globally: Admin only - install roles/collections for all users
            force: Reinstall items that are already installed
            no_deps: Skip dependencies of the selected items

        Returns:
            Install result
        """
        guard = await require_v2(client, "Content sources")
        if guard:
            return guard

        before = {
            r.get("name"): r.get("version")
            for r in (await client.list_ansible_resources() or [])
            if isinstance(r, dict)
        }

        result = await client.install_from_source(
            source_id,
            templates=templates,
            blueprints=blueprints,
            roles=roles,
            collections=collections,
            install_globally=install_globally,
            force=force,
            no_deps=no_deps,
        )

        # Ludus reports ok:true with the NEW version number while silently
        # keeping an existing older role unless force=True. Diff what is
        # actually installed against what the install claimed, so a silent
        # no-op cannot masquerade as an upgrade.
        after = {
            r.get("name"): r.get("version")
            for r in (await client.list_ansible_resources() or [])
            if isinstance(r, dict)
        }
        claimed: dict[str, str] = {}
        for section in ("blueprintResults", "localAnsibleResults"):
            block = result.get(section) if isinstance(result, dict) else None
            if not isinstance(block, dict):
                continue
            for key in ("ansibleResults", "roleResults", "collectionResults"):
                for item in block.get(key) or []:
                    if isinstance(item, dict) and item.get("name") and item.get("version"):
                        claimed[item["name"]] = item["version"]

        stale = [
            {"role": name, "claimed": version, "actually_installed": after.get(name)}
            for name, version in claimed.items()
            if after.get(name) is not None and after.get(name) != version
        ]

        response: dict[str, Any] = {"result": format_tool_response(result)}
        if stale:
            response["warning"] = (
                "Ludus reported installing versions that are NOT what ended up "
                "installed - an existing copy was kept. Re-run with force=True."
            )
            response["version_mismatches"] = stale
        changed = {n: v for n, v in after.items() if before.get(n) != v}
        if changed:
            response["updated"] = changed
        return response

    @mcp.tool()
    async def add_source(
        source_id: str,
        url: str | None = None,
        source_type: str = "git",
        ref: str | None = None,
        archive_path: str | None = None,
        make_global: bool = False,
        force: bool = False,
    ) -> dict:
        """Register a new content source on the Ludus server.

        This is how you add a catalog of templates, roles and prebuilt labs
        that the server does not ship with. Adding a source does not install
        anything from it — follow with get_source_catalog then
        install_from_source.

        Args:
            source_id: ID to give the source, e.g. "ludus-source-bsl"
            url: Git URL. Required when source_type is "git".
            source_type: "git" for a repository, "archive" for a local tarball
            ref: Branch, tag or commit to track. Defaults to the default branch.
            archive_path: Path to a .tar.gz. Required when source_type is "archive".
            make_global: Make the source available to all users (admin only)
            force: Overwrite an existing source with the same ID
        """
        guard = await require_v2(client, "Content sources")
        if guard:
            return guard

        if source_type not in ("git", "archive"):
            return {
                "error": f"Unknown source_type '{source_type}'",
                "hint": "Use 'git' for a repository or 'archive' for a local tarball",
            }
        if source_type == "git" and not url:
            return {"error": "url is required when source_type is 'git'"}
        if source_type == "archive" and not archive_path:
            return {"error": "archive_path is required when source_type is 'archive'"}

        result = await client.add_source(
            source_id, source_type, url, ref, archive_path, make_global, force
        )
        return format_tool_response(
            {
                "sourceID": source_id,
                "result": result,
                "next_step": (
                    f"Nothing is installed yet. Run get_source_catalog('{source_id}') "
                    "to see what it publishes, then install_from_source to install."
                ),
            }
        )

    @mcp.tool()
    async def update_source(
        source_id: str,
        url: str | None = None,
        ref: str | None = None,
        archive_path: str | None = None,
        make_global: bool | None = None,
        force: bool = False,
    ) -> dict:
        """Update an existing source's URL, tracked ref, or backing archive.

        Changing the ref is how you move a source onto a different branch or
        pin it to a tag. Follow with sync_source to re-fetch the catalog.

        Args:
            source_id: Source to update
            url: New git URL
            ref: New branch, tag or commit to track
            archive_path: Path to a replacement .tar.gz
            make_global: Change whether all users can see the source
            force: Apply even if the source has local modifications
        """
        guard = await require_v2(client, "Content sources")
        if guard:
            return guard

        if url is None and ref is None and archive_path is None and make_global is None:
            return {
                "error": "Nothing to update",
                "hint": "Pass at least one of url, ref, archive_path, make_global",
            }

        result = await client.update_source(
            source_id, url, ref, archive_path, make_global, force
        )
        return format_tool_response(
            {
                "sourceID": source_id,
                "result": result,
                "next_step": f"Run sync_source('{source_id}') to refresh its catalog.",
            }
        )

    @mcp.tool()
    async def sync_source(source_id: str) -> dict:
        """Re-fetch a source so its catalog reflects the current upstream.

        Args:
            source_id: Source ID
        """
        guard = await require_v2(client, "Content sources")
        if guard:
            return guard
        return format_tool_response(await client.sync_source(source_id))

    @mcp.tool()
    async def delete_source(source_id: str) -> dict:
        """Remove a content source.

        This does not uninstall items the source already installed.

        Args:
            source_id: Source ID to remove
        """
        guard = await require_v2(client, "Content sources")
        if guard:
            return guard
        return format_tool_response(await client.delete_source(source_id))

    return mcp
