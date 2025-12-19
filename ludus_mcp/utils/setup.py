"""Interactive setup utility for Ludus MCP configuration."""

import os
import sys
from pathlib import Path
from typing import Any

from .config import get_settings
from .logging import get_logger

logger = get_logger(__name__)


def prompt_input(prompt: str, default: str | None = None, secret: bool = False) -> str:
    """Prompt user for input with optional default value."""
    if default:
        prompt_text = f"{prompt} [{default}]: "
    else:
        prompt_text = f"{prompt}: "
    
    if secret:
        import getpass
        value = getpass.getpass(prompt_text)
    else:
        value = input(prompt_text).strip()
    
    return value if value else (default or "")


def prompt_yes_no(prompt: str, default: bool = True) -> bool:
    """Prompt user for yes/no input."""
    default_text = "Y/n" if default else "y/N"
    response = input(f"{prompt} [{default_text}]: ").strip().lower()
    
    if not response:
        return default
    
    return response in ("y", "yes")


def validate_url(url: str) -> bool:
    """Validate URL format."""
    return url.startswith(("http://", "https://"))


def validate_file_path(path: str) -> bool:
    """Validate that a file path exists."""
    return Path(path).exists()


def interactive_setup() -> int:
    """Interactive setup wizard for Ludus MCP configuration."""
    print("=" * 60)
    print("Ludus MCP Configuration Setup")
    print("=" * 60)
    print()
    
    settings = get_settings()
    config: dict[str, Any] = {}
    
    # Ludus API Configuration
    print("Ludus API Configuration")
    print("-" * 60)
    
    api_url = prompt_input(
        "Ludus API URL",
        default=settings.ludus_api_url or "http://localhost:8080"
    )
    if not validate_url(api_url):
        print("ERROR: URL must start with http:// or https://", file=sys.stderr)
        return 1
    config["LUDUS_API_URL"] = api_url
    
    api_key = prompt_input(
        "Ludus API Key",
        default=settings.ludus_api_key or "",
        secret=True
    )
    if not api_key:
        print("WARNING: API key is required for most operations", file=sys.stderr)
    config["LUDUS_API_KEY"] = api_key
    
    print()
    
    # LLM Configuration (Optional)
    print("LLM Configuration (Optional)")
    print("-" * 60)
    print("Press Enter to skip LLM configuration (fallback parser will be used)")
    print()
    
    use_llm = prompt_yes_no("Do you want to configure an LLM?", default=False)
    
    if use_llm:
        print("\nSupported providers:")
        print("  1. llama-cpp (Local: Mistral 7B, Llama, etc.) - Auto-install available")
        print("  2. gpt4all (Local alternative) - Auto-install available")
        print("  3. ollama (Local Ollama server)")
        print("  4. openai (ChatGPT: GPT-4o, GPT-4, GPT-3.5)")
        print("  5. anthropic (Claude: Claude 3.5 Sonnet, Claude 3 Opus)")
        print("  6. google (Gemini: Gemini 1.5 Pro, Gemini Pro)")
        print()
        
        provider_choice = prompt_input(
            "LLM Provider (llama-cpp, gpt4all, ollama, openai, anthropic, google)",
            default=getattr(settings, "llm_provider_type", None) or "llama-cpp"
        )
        
        valid_providers = ["llama-cpp", "gpt4all", "ollama", "openai", "anthropic", "google"]
        if provider_choice not in valid_providers:
            print(f"WARNING: Invalid provider, defaulting to llama-cpp", file=sys.stderr)
            provider_choice = "llama-cpp"
        
        config["LLM_PROVIDER_TYPE"] = provider_choice
        
        # Cloud providers need API key
        if provider_choice in ["openai", "anthropic", "google"]:
            api_key = prompt_input(
                f"{provider_choice.title()} API Key",
                default=getattr(settings, "llm_api_key", None) or "",
                secret=True
            )
            if not api_key:
                print(f"WARNING: API key is required for {provider_choice}", file=sys.stderr)
            config["LLM_API_KEY"] = api_key
            
            # Model selection for cloud providers (latest models)
            default_models = {
                "openai": "gpt-4o",
                "anthropic": "claude-3-5-sonnet-20241022",
                "google": "gemini-1.5-pro",
            }
            model = prompt_input(
                "Model name",
                default=getattr(settings, "llm_model", None) or default_models.get(provider_choice, "")
            )
            config["LLM_MODEL"] = model
        
        # Local providers need model path or Ollama config
        elif provider_choice == "ollama":
            base_url = prompt_input(
                "Ollama base URL",
                default=getattr(settings, "llm_ollama_base_url", None) or "http://localhost:11434"
            )
            config["LLM_OLLAMA_BASE_URL"] = base_url
            
            model = prompt_input(
                "Ollama model name",
                default=getattr(settings, "llm_model", None) or "mistral"
            )
            config["LLM_MODEL"] = model
        
        else:  # llama-cpp or gpt4all
            model_path = prompt_input(
                "LLM Model Path",
                default=getattr(settings, "llm_model_path", None) or ""
            )
            if model_path and not validate_file_path(model_path):
                print(f"\n⚠ Model file not found: {model_path}")
                print()
                
                # Offer to install the model
                try:
                    from .model_installer import ModelInstaller
                    
                    installer = ModelInstaller(model_path, interactive=True)
                    results = installer.run_checks()
                    
                    print("Running model installation checks...")
                    print("-" * 60)
                    for message in results["messages"]:
                        print(f"  {message}")
                    print("-" * 60)
                    print()
                    
                    if results["checks_passed"]:
                        if results.get("model_info"):
                            print("Model Information:")
                            print(f"  Name: {results['model_info']['name']}")
                            print(f"  Size: ~{results['model_info']['size_gb']} GB")
                            print(f"  Description: {results['model_info']['description']}")
                            print()
                        
                        install_model = prompt_yes_no(
                            "Would you like to download and install this model now?",
                            default=True
                        )
                        
                        if install_model:
                            print()
                            if installer.install_model_interactive():
                                print()
                                print("[OK] Model installed successfully!")
                                # Model path is already set, continue
                            else:
                                print()
                                print("⚠ Model installation failed or cancelled")
                                if not prompt_yes_no("Continue without model?", default=False):
                                    model_path = ""
                        else:
                            print("ℹ Skipping model installation. You can install it later with:")
                            print(f"   python3 scripts/install_model.py {model_path}")
                            if not prompt_yes_no("Continue without model?", default=False):
                                model_path = ""
                    else:
                        print("⚠ Pre-installation checks failed. Cannot install model automatically.")
                        print()
                        print("Please fix the following issues:")
                        if not results.get("has_disk_space", True):
                            print("  - Free up disk space")
                        if not results.get("has_download_tool", False):
                            print("  - Install wget or curl: sudo apt-get install wget")
                        if not results.get("has_internet", False):
                            print("  - Check your internet connection")
                        print()
                        print("You can install the model manually later with:")
                        print(f"   python3 scripts/install_model.py {model_path}")
                        print()
                        if not prompt_yes_no("Continue without model?", default=False):
                            model_path = ""
                except ImportError:
                    print("⚠ Model installer not available")
                    if not prompt_yes_no("Continue anyway?", default=False):
                        model_path = ""
                except Exception as e:
                    logger.warning(f"Error during model installation check: {e}")
                    if not prompt_yes_no("Continue anyway?", default=False):
                        model_path = ""
            config["LLM_MODEL_PATH"] = model_path
            
            if model_path:
                context_size = prompt_input(
                    "Context Size",
                    default=str(getattr(settings, "llm_context_size", None) or 4096)
                )
                try:
                    config["LLM_CONTEXT_SIZE"] = int(context_size)
                except ValueError:
                    config["LLM_CONTEXT_SIZE"] = 4096
        
        # Common settings
        temperature = prompt_input(
            "Temperature (0.0-1.0)",
            default=str(getattr(settings, "llm_temperature", None) or 0.7)
        )
        try:
            config["LLM_TEMPERATURE"] = float(temperature)
        except ValueError:
            config["LLM_TEMPERATURE"] = 0.7
    
    print()
    
    # Logging Configuration
    print("Logging Configuration")
    print("-" * 60)
    log_level = prompt_input(
        "Log Level (DEBUG, INFO, WARNING, ERROR)",
        default=settings.log_level or "INFO"
    )
    if log_level.upper() not in ("DEBUG", "INFO", "WARNING", "ERROR"):
        log_level = "INFO"
    config["LOG_LEVEL"] = log_level.upper()
    
    print()
    
    # Save Configuration
    print("=" * 60)
    save_to_file = prompt_yes_no("Save configuration to .env file?", default=True)
    
    if save_to_file:
        env_file = Path(".env")
        if env_file.exists():
            overwrite = prompt_yes_no(".env file already exists. Overwrite?", default=False)
            if not overwrite:
                print("Configuration not saved.")
                return 0
        
        try:
            with open(env_file, "w") as f:
                f.write("# Ludus MCP Configuration\n")
                f.write("# Generated by interactive setup\n\n")
                for key, value in config.items():
                    if value:  # Only write non-empty values
                        # Escape special characters in values
                        if "\n" in str(value) or '"' in str(value):
                            value = repr(str(value))
                        f.write(f"{key}={value}\n")
            
            print(f"[OK] Configuration saved to {env_file.absolute()}")
        except Exception as e:
            print(f"ERROR: Failed to save configuration: {e}", file=sys.stderr)
            return 1
    else:
        # Show environment variables to set
        print("\nSet these environment variables:")
        print("-" * 60)
        for key, value in config.items():
            if value:
                print(f"export {key}={value}")
        print()
    
    # Test Configuration
    print("=" * 60)
    test_config = prompt_yes_no("Test configuration now?", default=True)
    
    if test_config:
        print("\nTesting configuration...")
        
        # Test API connection
        if config.get("LUDUS_API_URL") and config.get("LUDUS_API_KEY"):
            try:
                import httpx
                import asyncio
                
                async def test_connection():
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        try:
                            # Try a simple API endpoint (ranges list is usually available)
                            response = await client.get(
                                f"{config['LUDUS_API_URL']}/api/ranges",
                                headers={"Authorization": f"Bearer {config['LUDUS_API_KEY']}"}
                            )
                            if response.status_code == 200:
                                print("[OK] API connection successful")
                                return True
                            elif response.status_code == 401:
                                print("⚠ API connection failed: Invalid API key")
                                return False
                            elif response.status_code == 404:
                                # API might not have /api/ranges, but connection works
                                print("[OK] API connection successful (endpoint may vary)")
                                return True
                            else:
                                print(f"⚠ API returned status {response.status_code}")
                                return False
                        except httpx.ConnectError:
                            print("⚠ Could not connect to API (this may be normal if API is not running)")
                            return False
                        except httpx.RequestError as e:
                            print(f"⚠ Connection error: {e}")
                            return False
                
                asyncio.run(test_connection())
            except ImportError:
                print("⚠ Cannot test API connection (httpx not available)")
            except Exception as e:
                print(f"⚠ Error testing API connection: {e}")
        else:
            print("⚠ Skipping API test (URL or key not provided)")
        
        # Test LLM
        if config.get("LLM_MODEL_PATH"):
            model_path = Path(config["LLM_MODEL_PATH"])
            if model_path.exists():
                print("[OK] LLM model file found")
                # Verify model integrity
                try:
                    from .model_installer import ModelInstaller
                    installer = ModelInstaller(str(model_path), interactive=False)
                    is_valid, msg = installer.verify_model_file()
                    if is_valid:
                        print(f"[OK] {msg}")
                    else:
                        print(f"⚠ {msg}")
                except Exception:
                    pass  # Skip verification if installer not available
            else:
                print("⚠ LLM model file not found")
                print("   You can install it later with:")
                print(f"   python3 scripts/install_model.py {config['LLM_MODEL_PATH']}")
        elif config.get("LLM_PROVIDER_TYPE") in ["openai", "anthropic", "google", "ollama"]:
            print("[OK] LLM configured (cloud provider, no local model needed)")
        else:
            print("ℹ LLM not configured (will use fallback parser)")
    
    print()
    print("=" * 60)
    print("Setup complete!")
    print("=" * 60)
    
    if save_to_file:
        print(f"\nConfiguration saved to: {Path('.env').absolute()}")
        print("You can now run: ludus-fastmcp")
    else:
        print("\nRemember to set the environment variables before running ludus-fastmcp")
    
    return 0

