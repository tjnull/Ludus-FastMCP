"""Configuration management using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Ludus API Configuration
    ludus_api_url: str = "http://localhost:8080"
    ludus_api_key: str = ""
    ludus_ssl_verify: bool = False  # Default False for self-signed certs in lab environments

    # LLM Configuration (supports multiple providers)
    llm_provider_type: str = "llama-cpp"  # llama-cpp, gpt4all, openai, anthropic, google, ollama
    llm_api_key: str = ""  # For cloud providers (OpenAI, Anthropic, Google)
    llm_model_path: str = ""  # For local models (llama-cpp, gpt4all)
    llm_model: str = ""  # Model name (e.g., "gpt-4o", "claude-3-5-sonnet-20241022", "gemini-pro", "mistral")
    llm_context_size: int = 4096  # For local models
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2048
    llm_ollama_base_url: str = "http://localhost:11434"  # For Ollama

    # MCP Server Configuration
    mcp_server_name: str = "ludus-fastmcp"
    mcp_server_version: str = "0.1.0"

    # Logging
    log_level: str = "INFO"


_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

