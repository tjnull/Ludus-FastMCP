"""Configuration management using Pydantic Settings."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_env_files() -> tuple[str, ...]:
    """Get list of .env files to load, in order of priority (later overrides earlier)."""
    env_files = []

    # 1. User's home config directory (lowest priority)
    home_env = Path.home() / ".ludus-fastmcp" / ".env"
    if home_env.exists():
        env_files.append(str(home_env))

    # 2. Current working directory (highest priority)
    cwd_env = Path.cwd() / ".env"
    if cwd_env.exists():
        env_files.append(str(cwd_env))

    return tuple(env_files) if env_files else (".env",)


def _load_env_files_to_environ():
    """Manually load .env files into os.environ to ensure they're available.

    This is needed because pydantic-settings evaluates env_file at class definition
    time, but the MCP server may be started from different directories.
    """
    from dotenv import dotenv_values

    # Load from home config first (lower priority)
    home_env = Path.home() / ".ludus-fastmcp" / ".env"
    if home_env.exists():
        values = dotenv_values(home_env)
        for key, value in values.items():
            if key not in os.environ and value is not None:
                os.environ[key] = value

    # Load from cwd (higher priority, will override)
    cwd_env = Path.cwd() / ".env"
    if cwd_env.exists():
        values = dotenv_values(cwd_env)
        for key, value in values.items():
            if key not in os.environ and value is not None:
                os.environ[key] = value


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=_get_env_files(),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Ludus API Configuration
    ludus_api_url: str = "http://localhost:8080"
    ludus_api_key: str = ""
    ludus_ssl_verify: bool = False  # Default False for self-signed certs in lab environments
    ludus_api_version: str = "auto"  # "auto", "v1", or "v2"
    ludus_jwt_token: str = ""  # JWT Bearer token for Pro/SSO users

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
    mcp_server_version: str = "2.0.0"

    # Logging
    log_level: str = "INFO"


_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create the global settings instance."""
    global _settings
    if _settings is None:
        # Load .env files into environment before creating settings
        _load_env_files_to_environ()
        _settings = Settings()
    return _settings
