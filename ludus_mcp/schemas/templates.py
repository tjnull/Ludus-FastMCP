"""Template-related schemas."""

from pydantic import BaseModel, Field


class TemplateApply(BaseModel):
    """Request schema for applying a template."""

    template_name: str = Field(..., description="Name of the template to apply")
    host_id: str = Field(..., description="ID of the host to apply template to")
    parameters: dict[str, str] | None = Field(
        None, description="Optional template parameters"
    )


class Template(BaseModel):
    """Template response schema."""

    name: str = Field(..., description="Template name")
    built: bool | None = Field(None, description="Whether template is built")
    description: str | None = Field(None, description="Template description")
    os_type: str | None = Field(None, description="Operating system type")
    os_version: str | None = Field(None, description="Operating system version")
    default_cpu: int | None = Field(None, description="Default CPU count")
    default_memory: int | None = Field(None, description="Default memory in MB")
    default_disk: int | None = Field(None, description="Default disk size in GB")


class TemplateAdd(BaseModel):
    """Request schema for adding a template."""

    directory: str = Field(..., description="Path to template directory")
    force: bool = Field(
        default=False,
        description="Remove existing template directory if it exists"
    )


class TemplateBuild(BaseModel):
    """Request schema for building a template."""

    template_name: str = Field(
        default="all",
        description="Name of template to build, or 'all' for all templates"
    )
    parallel: int = Field(
        default=1,
        ge=1,
        description="Number of templates to build in parallel"
    )


class TemplateDelete(BaseModel):
    """Request schema for deleting a template."""

    template_name: str = Field(..., description="Name of template to delete")

