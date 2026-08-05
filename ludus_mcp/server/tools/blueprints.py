"""Blueprint management FastMCP tools for Ludus MCP server."""

from typing import Any
from fastmcp import FastMCP
from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.server.handlers.blueprints import BlueprintHandler
from ludus_mcp.server.handlers.validation import ValidationHandler
from ludus_mcp.server.tools.utils import LazyHandlerRegistry, format_tool_response
from ludus_mcp.utils.version_guard import require_v2


def create_blueprint_tools(client: LudusAPIClient) -> FastMCP:
    """Create blueprint management tools.

    Args:
        client: Ludus API client

    Returns:
        FastMCP instance with blueprint tools registered
    """
    mcp = FastMCP("Blueprints")
    registry = LazyHandlerRegistry(client)

    # Ludus always deploys a router VM from this template first, whatever the
    # range config says. A range cannot deploy without it, and the failure
    # surfaces as an opaque Ansible error deep in the run.
    ROUTER_TEMPLATE = "debian-11-x64-server-template"

    @mcp.tool()
    async def deploy_range_from_blueprint(
        blueprint_id: str,
        range_id: str | None = None,
        destroy_existing: bool = False,
        deploy: bool = True,
        dry_run: bool = False,
        user_id: str | None = None,
    ) -> dict:
        """Set up and deploy a whole range from a blueprint in one call.

        Runs the full sequence with pre-flight checks that otherwise fail late
        and cryptically:

        1. Confirms the blueprint exists
        2. Checks every template the blueprint needs is BUILT (including the
           router template Ludus always requires) and stops with the exact
           build command if not
        3. Optionally destroys the existing range
        4. Applies the blueprint to the range config
        5. Validates the resulting config
        6. Starts the deployment

        Deployment continues in the background; poll get_range for state and
        get_range_logs for progress. A multi-VM lab such as GOAD takes hours.

        Args:
            blueprint_id: Blueprint to deploy (e.g. "ludus-source-bsl/goad")
            range_id: Range to deploy into (defaults to the caller's range)
            destroy_existing: Destroy the current range VMs first, for a clean
                deploy rather than reconciling against what is already there
            deploy: Set False to apply the blueprint and validate WITHOUT
                deploying. Note this still OVERWRITES the range config.
            dry_run: Only run the read-only checks (blueprint present, templates
                built). Changes nothing - use this to test before committing.
            user_id: Optional user ID (admin only)

        Returns:
            A step-by-step report of what was done, or where it stopped
        """
        guard = await require_v2(client, "Blueprints")
        if guard:
            return guard

        steps: list[dict[str, Any]] = []

        def record(step: str, ok: bool, detail: Any = None) -> None:
            steps.append({"step": step, "ok": ok, "detail": detail})

        def stop(reason: str, **extra: Any) -> dict:
            return {"status": "failed", "error": reason, "steps": steps, **extra}

        # 1. blueprint present?
        blueprints = await client.list_blueprints()
        known = {b.get("blueprintID") for b in blueprints if isinstance(b, dict)}
        if blueprint_id not in known:
            record("find blueprint", False, sorted(x for x in known if x))
            return stop(
                f"Blueprint {blueprint_id!r} is not installed on this server.",
                available=sorted(x for x in known if x),
                hint="Use get_source_catalog and install_from_source to add it.",
            )
        record("find blueprint", True, blueprint_id)

        # 2. are the templates it needs actually built?
        templates = await client.list_templates()
        built = {t.get("name") for t in templates if isinstance(t, dict) and t.get("built")}
        known_templates = {t.get("name") for t in templates if isinstance(t, dict)}

        required: set[str] = set()
        try:
            config_result = await client.get_blueprint_config(blueprint_id)
            config_text = str(
                config_result.get("result", config_result)
                if isinstance(config_result, dict)
                else config_result
            )
            for name in known_templates:
                if name and name in config_text:
                    required.add(name)
        except Exception as e:  # config is a nicety; never block the deploy on it
            record("read blueprint config", False, str(e))

        required.add(ROUTER_TEMPLATE)
        missing = sorted(t for t in required if t not in built)
        if missing:
            record("check templates built", False, missing)
            return stop(
                "Required templates are not built yet: " + ", ".join(missing),
                missing_templates=missing,
                hint=f"build_template(templates={missing!r}) - this takes a while, "
                     "then re-run this tool.",
            )
        record("check templates built", True, sorted(required))

        # 2b. are the Ansible roles the blueprint needs actually installed?
        # A blueprint written for role vN against an installed vN-1 fails deep
        # in the Ansible run with an error that points nowhere near the cause.
        try:
            installed_roles = {
                r.get("name"): r.get("version")
                for r in (await client.list_ansible_resources() or [])
                if isinstance(r, dict)
            }
            catalog_required: list[str] = []
            for source in await client.list_sources():
                sid = source.get("sourceID") if isinstance(source, dict) else None
                if not sid or not blueprint_id.startswith(f"{sid}/"):
                    continue
                catalog = await client.get_source_catalog(sid)
                section = catalog.get("blueprints", {})
                items = section.get("items") if isinstance(section, dict) else section
                short_id = blueprint_id.split("/", 1)[1]
                for entry in items or []:
                    if not isinstance(entry, dict):
                        continue
                    if entry.get("id") == short_id or entry.get("sourceBlueprintID") == short_id:
                        catalog_required = list(entry.get("requiredRoles") or [])
                        break

            missing_roles = [r for r in catalog_required if r not in installed_roles]
            if missing_roles:
                record("check roles installed", False, missing_roles)
                return stop(
                    "Required Ansible roles are not installed: " + ", ".join(missing_roles),
                    missing_roles=missing_roles,
                    hint="install_from_source(..., blueprints=[...], force=True) installs "
                         "a blueprint's roles; force=True is needed to replace older copies.",
                )
            if catalog_required:
                record("check roles installed", True,
                       {r: installed_roles.get(r) for r in catalog_required})
        except Exception as e:
            # Never block a deploy because the catalog lookup itself failed
            record("check roles installed", False, f"could not verify: {e}")

        if dry_run:
            return {
                "status": "ok",
                "dry_run": True,
                "blueprint": blueprint_id,
                "steps": steps,
                "note": "Nothing was changed. Re-run without dry_run to apply and deploy.",
            }

        # 3. refuse to overwrite the config of a range that is mid-deploy
        try:
            current = await client.get_range(user_id)
            state = str(current.get("rangeState", "")).upper()
        except Exception:
            state = ""
        if state in {"DEPLOYING", "TESTING"}:
            record("check range is idle", False, state)
            return stop(
                f"Range is currently {state}; applying a blueprint would overwrite the "
                "config of a run in progress.",
                range_state=state,
                hint="Wait for it to finish, or call abort_range_deployment first.",
            )
        record("check range is idle", True, state or "unknown")

        # 4. resolve the target range - apply needs a concrete rangeID
        target_range = range_id
        if not target_range:
            try:
                range_info = await client.get_range(user_id)
                target_range = range_info.get("rangeID")
            except Exception as e:
                record("resolve range", False, str(e))
                return stop(f"Could not determine which range to deploy into: {e}")
        if not target_range:
            record("resolve range", False, None)
            return stop("Could not determine a range ID; pass range_id explicitly.")
        record("resolve range", True, target_range)

        # 5. clear the range first if asked
        if destroy_existing:
            try:
                # user_id is explicit here, satisfying delete_range's safety check
                result = await client.delete_range(
                    user_id=user_id, require_explicit_user=False
                )
                record("destroy existing range", True, result)
            except Exception as e:
                record("destroy existing range", False, str(e))
                return stop(f"Could not destroy the existing range: {e}")

        # 6. apply
        try:
            applied = await client.apply_blueprint(blueprint_id, target_range)
            record("apply blueprint", True, applied)
        except Exception as e:
            record("apply blueprint", False, str(e))
            return stop(f"Could not apply the blueprint: {e}")

        # 7. validate what we ended up with
        try:
            config = await client.get_range_config(user_id)
            handler = registry.get_handler("validation", ValidationHandler)
            validation = await handler.validate_config(config)
            data = validation if isinstance(validation, dict) else validation.__dict__
            record("validate config", bool(data.get("valid", True)), {
                "valid": data.get("valid"),
                "errors": [getattr(e, "message", str(e)) for e in data.get("errors", [])],
            })
            if data.get("valid") is False:
                return stop(
                    "The applied config did not validate; nothing was deployed.",
                    errors=[getattr(e, "message", str(e)) for e in data.get("errors", [])],
                )
        except Exception as e:
            record("validate config", False, str(e))

        if not deploy:
            return {"status": "prepared", "deployed": False, "steps": steps,
                    "next": "Call deploy_range when ready."}

        # 8. go
        try:
            started = await client.deploy_range(user_id=user_id)
            record("start deployment", True, started)
        except Exception as e:
            record("start deployment", False, str(e))
            return stop(f"Deployment did not start: {e}")

        return {
            "status": "deploying",
            "blueprint": blueprint_id,
            "range_id": target_range,
            "steps": steps,
            "next": "Deployment runs in the background - poll get_range for rangeState "
                    "and get_range_logs for progress. Multi-VM labs take hours.",
        }

    @mcp.tool()
    async def list_blueprints(
        from_source: str | None = None, tag: str | None = None
    ) -> list | dict:
        """List all available blueprints.

        Args:
            from_source: Only list blueprints published by this source ID
            tag: Only list blueprints carrying this tag

        Returns:
            List of blueprints with their metadata
        """
        guard = await require_v2(client, "Blueprints")
        if guard:
            return guard
        if from_source or tag:
            return format_tool_response(await client.list_blueprints(from_source, tag))
        handler = registry.get_handler("blueprint", BlueprintHandler)
        result = await handler.list_blueprints()
        return format_tool_response(result)

    @mcp.tool()
    async def get_blueprint(blueprint_id: str) -> dict:
        """Get a blueprint's metadata: name, description, version, tags, source.

        Use get_blueprint_config for the range configuration it deploys.

        Args:
            blueprint_id: Blueprint ID
        """
        guard = await require_v2(client, "Blueprints")
        if guard:
            return guard
        return format_tool_response(await client.get_blueprint(blueprint_id))

    @mcp.tool()
    async def create_blueprint(
        blueprint_id: str,
        config: dict | None = None,
        name: str | None = None,
        description: str | None = None,
        version: str | None = None,
        tags: list[str] | None = None,
        min_ludus_version: str | None = None,
    ) -> dict:
        """Create a blueprint from a range configuration you already have.

        Use create_blueprint_from_range instead when you want to capture a
        deployed range rather than supply the config yourself.

        Args:
            blueprint_id: Unique identifier for the blueprint
            config: Range configuration the blueprint deploys
            name: Human-readable name
            description: What the blueprint builds
            version: Version string, e.g. "1.0.0"
            tags: Tags used for discovery and filtering
            min_ludus_version: Minimum Ludus version required
        """
        guard = await require_v2(client, "Blueprints")
        if guard:
            return guard
        result = await client.create_blueprint(
            blueprint_id, config, name, description, version, tags, min_ludus_version
        )
        return format_tool_response(result)

    @mcp.tool()
    async def export_blueprint(blueprint_id: str, output_path: str) -> dict:
        """Export a blueprint to a .tar.gz archive on disk.

        The archive can be moved to another Ludus server and loaded there with
        import_blueprint.

        Args:
            blueprint_id: Blueprint to export
            output_path: Where to write the archive, e.g. "/tmp/goad.tar.gz"
        """
        guard = await require_v2(client, "Blueprints")
        if guard:
            return guard
        return format_tool_response(await client.export_blueprint(blueprint_id, output_path))

    @mcp.tool()
    async def import_blueprint(archive_path: str) -> dict:
        """Import a blueprint from a .tar.gz archive.

        Args:
            archive_path: Path to an archive produced by export_blueprint
        """
        guard = await require_v2(client, "Blueprints")
        if guard:
            return guard
        return format_tool_response(await client.import_blueprint(archive_path))

    @mcp.tool()
    async def install_blueprint(
        blueprint_id: str, make_global: bool = False, force_roles: bool = False
    ) -> dict:
        """Install a blueprint's Ansible role and collection dependencies.

        Run this before deploying a blueprint that came from a content source.
        Without it the deployment fails partway through on missing roles, after
        the VMs have already been cloned.

        Args:
            blueprint_id: Blueprint whose dependencies to install
            make_global: Install roles for all users (admin only)
            force_roles: Reinstall roles that are already present
        """
        guard = await require_v2(client, "Blueprints")
        if guard:
            return guard
        result = await client.install_blueprint(blueprint_id, make_global, force_roles)
        return format_tool_response(result)

    @mcp.tool()
    async def create_blueprint_from_range(range_id: str) -> dict:
        """Create a reusable blueprint from an existing range.

        Args:
            range_id: ID of the range to create a blueprint from

        Returns:
            Created blueprint details
        """
        guard = await require_v2(client, "Blueprints")
        if guard:
            return guard
        handler = registry.get_handler("blueprint", BlueprintHandler)
        result = await handler.create_blueprint_from_range(range_id)
        return format_tool_response(result)

    @mcp.tool()
    async def apply_blueprint_to_range(blueprint_id: str, range_id: str) -> dict:
        """Apply a blueprint to a range.

        Args:
            blueprint_id: ID of the blueprint to apply
            range_id: ID of the range to apply the blueprint to

        Returns:
            Result of the apply operation
        """
        guard = await require_v2(client, "Blueprints")
        if guard:
            return guard
        handler = registry.get_handler("blueprint", BlueprintHandler)
        result = await handler.apply_blueprint(blueprint_id, range_id)
        return format_tool_response(result)

    @mcp.tool()
    async def copy_blueprint(
        blueprint_id: str,
        new_blueprint_id: str | None = None,
        name: str | None = None,
        description: str | None = None,
    ) -> dict:
        """Copy a blueprint under a new ID.

        Copy before editing when you want to keep the original intact, e.g.
        forking a source-provided lab to customise it.

        Args:
            blueprint_id: ID of the blueprint to copy
            new_blueprint_id: ID for the copy. Server generates one if omitted.
            name: Name for the copy
            description: Description for the copy

        Returns:
            Copied blueprint details
        """
        guard = await require_v2(client, "Blueprints")
        if guard:
            return guard
        result = await client.copy_blueprint(
            blueprint_id, new_blueprint_id, name, description
        )
        return format_tool_response(result)

    @mcp.tool()
    async def delete_blueprint(blueprint_id: str) -> dict:
        """Delete a blueprint.

        Args:
            blueprint_id: ID of the blueprint to delete

        Returns:
            Deletion confirmation
        """
        guard = await require_v2(client, "Blueprints")
        if guard:
            return guard
        handler = registry.get_handler("blueprint", BlueprintHandler)
        result = await handler.delete_blueprint(blueprint_id)
        return format_tool_response(result)

    @mcp.tool()
    async def get_blueprint_config(blueprint_id: str) -> dict:
        """Get blueprint configuration.

        Args:
            blueprint_id: ID of the blueprint

        Returns:
            Blueprint configuration details
        """
        guard = await require_v2(client, "Blueprints")
        if guard:
            return guard
        handler = registry.get_handler("blueprint", BlueprintHandler)
        result = await handler.get_blueprint_config(blueprint_id)
        return format_tool_response(result)

    @mcp.tool()
    async def update_blueprint_config(blueprint_id: str, config: dict) -> dict:
        """Update blueprint configuration.

        Args:
            blueprint_id: ID of the blueprint
            config: New configuration to apply

        Returns:
            Updated blueprint configuration
        """
        guard = await require_v2(client, "Blueprints")
        if guard:
            return guard
        handler = registry.get_handler("blueprint", BlueprintHandler)
        result = await handler.update_blueprint_config(blueprint_id, config)
        return format_tool_response(result)

    @mcp.tool()
    async def share_blueprint_with_users(blueprint_id: str, user_ids: list[str]) -> dict:
        """Share a blueprint with users.

        Args:
            blueprint_id: ID of the blueprint to share
            user_ids: List of user IDs to share with

        Returns:
            Share operation result
        """
        guard = await require_v2(client, "Blueprints")
        if guard:
            return guard
        handler = registry.get_handler("blueprint", BlueprintHandler)
        result = await handler.share_blueprint_with_users(blueprint_id, user_ids)
        return format_tool_response(result)

    @mcp.tool()
    async def unshare_blueprint_with_users(blueprint_id: str, user_ids: list[str]) -> dict:
        """Unshare a blueprint from users.

        Args:
            blueprint_id: ID of the blueprint to unshare
            user_ids: List of user IDs to remove access from

        Returns:
            Unshare operation result
        """
        guard = await require_v2(client, "Blueprints")
        if guard:
            return guard
        handler = registry.get_handler("blueprint", BlueprintHandler)
        result = await handler.unshare_blueprint_with_users(blueprint_id, user_ids)
        return format_tool_response(result)

    @mcp.tool()
    async def share_blueprint_with_groups(blueprint_id: str, group_names: list[str]) -> dict:
        """Share a blueprint with groups.

        Args:
            blueprint_id: ID of the blueprint to share
            group_names: List of group names to share with

        Returns:
            Share operation result
        """
        guard = await require_v2(client, "Blueprints")
        if guard:
            return guard
        handler = registry.get_handler("blueprint", BlueprintHandler)
        result = await handler.share_blueprint_with_groups(blueprint_id, group_names)
        return format_tool_response(result)

    @mcp.tool()
    async def unshare_blueprint_with_groups(blueprint_id: str, group_names: list[str]) -> dict:
        """Unshare a blueprint from groups.

        Args:
            blueprint_id: ID of the blueprint to unshare
            group_names: List of group names to remove access from

        Returns:
            Unshare operation result
        """
        guard = await require_v2(client, "Blueprints")
        if guard:
            return guard
        handler = registry.get_handler("blueprint", BlueprintHandler)
        result = await handler.unshare_blueprint_with_groups(blueprint_id, group_names)
        return format_tool_response(result)

    @mcp.tool()
    async def list_blueprint_access_users(blueprint_id: str) -> list | dict:
        """List users with access to a blueprint.

        Args:
            blueprint_id: ID of the blueprint

        Returns:
            List of users with access
        """
        guard = await require_v2(client, "Blueprints")
        if guard:
            return guard
        handler = registry.get_handler("blueprint", BlueprintHandler)
        result = await handler.list_blueprint_access_users(blueprint_id)
        return format_tool_response(result)

    @mcp.tool()
    async def list_blueprint_access_groups(blueprint_id: str) -> list | dict:
        """List groups with access to a blueprint.

        Args:
            blueprint_id: ID of the blueprint

        Returns:
            List of groups with access
        """
        guard = await require_v2(client, "Blueprints")
        if guard:
            return guard
        handler = registry.get_handler("blueprint", BlueprintHandler)
        result = await handler.list_blueprint_access_groups(blueprint_id)
        return format_tool_response(result)

    return mcp
