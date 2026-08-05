"""Template operation handlers."""

from pathlib import Path
from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.schemas.templates import Template, TemplateApply, TemplateAdd, TemplateBuild
from ludus_mcp.utils.logging import get_logger

logger = get_logger(__name__)


class TemplateHandler:
    """Handler for template operations."""

    def __init__(self, client: LudusAPIClient) -> None:
        """Initialize the template handler."""
        self.client = client

    async def list_templates(self, user_id: str | None = None) -> list[Template]:
        """List available templates."""
        logger.debug("Listing available templates")
        results = await self.client.list_templates()
        return [Template(**r) for r in results]

    async def apply_template(
        self, range_id: str, host_id: str, data: TemplateApply
    ) -> dict:
        """Apply a template to a host."""
        logger.debug(
            f"Applying template {data.template_name} to host {host_id} in range {range_id}"
        )
        return await self.client.apply_template(
            range_id, host_id, data.template_name, data.parameters
        )

    async def add_template(
        self, data: TemplateAdd, user_id: str | None = None
    ) -> dict:
        """Add a new template to Ludus.

        Args:
            data: Template add configuration
            user_id: Optional user ID (admin only)

        Returns:
            API response with add status
        """
        logger.info(f"Adding template from directory: {data.directory}")

        # Verify directory exists
        template_dir = Path(data.directory)
        if not template_dir.exists():
            raise ValueError(f"Template directory does not exist: {data.directory}")

        if not template_dir.is_dir():
            raise ValueError(f"Path is not a directory: {data.directory}")

        # The API takes the directory as an uncompressed tar upload; the client
        # builds the archive. A JSON payload describing the directory was
        # posted to /templates/add, which does not exist.
        return await self.client.add_template(
            str(template_dir.absolute()), force=data.force, user_id=user_id
        )

    async def build_template(
        self, data: TemplateBuild, user_id: str | None = None
    ) -> dict:
        """Build a template.

        Args:
            data: Template build configuration
            user_id: Optional user ID (admin only)

        Returns:
            API response with build status
        """
        template_name = data.template_name if data.template_name != "all" else None
        logger.info(f"Building template: {data.template_name} (parallel={data.parallel})")

        return await self.client.build_template(
            template_name=template_name,
            parallel=data.parallel,
            user_id=user_id
        )

    async def delete_template(
        self, template_name: str, user_id: str | None = None
    ) -> dict:
        """Delete a template.

        Args:
            template_name: Name of template to delete
            user_id: Optional user ID (admin only)

        Returns:
            API response with delete status
        """
        logger.info(f"Deleting template: {template_name}")
        return await self.client.delete_template(template_name, user_id)

    async def get_template_status(self, user_id: str | None = None) -> dict:
        """Get template build status.

        Args:
            user_id: Optional user ID (admin only)

        Returns:
            Template build status information
        """
        logger.debug("Getting template build status")
        return await self.client.get_template_status(user_id)

    async def get_template_logs(
        self, user_id: str | None = None, tail: int | None = None
    ) -> str:
        """Get template build logs.

        Args:
            user_id: Optional user ID (admin only)
            tail: Number of lines to tail (optional)

        Returns:
            Template build logs
        """
        logger.debug("Getting template build logs")
        return await self.client.get_template_logs(user_id, tail)

    async def abort_template_operation(self, user_id: str | None = None) -> dict:
        """Abort template build operation.

        Args:
            user_id: Optional user ID (admin only)

        Returns:
            API response
        """
        logger.info("Aborting template operation")
        return await self.client.abort_template_operation(user_id)
