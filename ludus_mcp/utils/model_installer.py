"""Model installation and verification utility."""

import os
import sys
import subprocess
from pathlib import Path
from typing import Any

from ludus_mcp.utils.logging import get_logger

logger = get_logger(__name__)


class ModelInstaller:
    """Handles model installation and verification."""

    # Popular models and their download URLs
    MODELS = {
        "mistral-7b-instruct-v0.2.Q4_K_M.gguf": {
            "name": "Mistral 7B Instruct (Q4_K_M)",
            "url": "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
            "size_gb": 4.1,
            "description": "Good balance of quality and size, recommended for most users",
        },
        "mistral-7b-instruct-v0.1.Q4_K_M.gguf": {
            "name": "Mistral 7B Instruct v0.1 (Q4_K_M)",
            "url": "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.1-GGUF/resolve/main/mistral-7b-instruct-v0.1.Q4_K_M.gguf",
            "size_gb": 4.1,
            "description": "Previous version, still excellent",
        },
    }

    def __init__(self, model_path: str, interactive: bool = True) -> None:
        """Initialize model installer.
        
        Args:
            model_path: Path to the model file
            interactive: Whether to prompt user for installation
        """
        self.model_path = Path(model_path)
        self.interactive = interactive
        self.models_dir = self.model_path.parent

    def check_model_exists(self) -> bool:
        """Check if model file exists."""
        return self.model_path.exists() and self.model_path.is_file()

    def check_disk_space(self, required_gb: float) -> tuple[bool, float, float]:
        """Check if there's enough disk space.
        
        Returns:
            (has_space, available_gb, required_gb)
        """
        try:
            # Create directory if it doesn't exist (for disk space check)
            check_dir = self.models_dir
            if not check_dir.exists():
                # Check parent directory instead
                check_dir = check_dir.parent
                if not check_dir.exists():
                    check_dir = check_dir.parent
            
            stat = os.statvfs(check_dir)
            available_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
            has_space = available_gb >= required_gb
            return has_space, available_gb, required_gb
        except Exception as e:
            logger.warning(f"Could not check disk space: {e}")
            return True, 0.0, required_gb  # Assume we have space if we can't check

    def check_download_tools(self) -> tuple[bool, str | None]:
        """Check if wget or curl is available.
        
        Returns:
            (has_tool, tool_name)
        """
        for tool in ["wget", "curl"]:
            try:
                subprocess.run(
                    [tool, "--version"],
                    capture_output=True,
                    check=True,
                )
                return True, tool
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        return False, None

    def check_internet_connection(self) -> bool:
        """Check if internet connection is available."""
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except OSError:
            return False

    def verify_model_file(self) -> tuple[bool, str]:
        """Verify model file integrity.
        
        Returns:
            (is_valid, message)
        """
        if not self.model_path.exists():
            return False, "Model file does not exist"
        
        if not self.model_path.is_file():
            return False, "Model path is not a file"
        
        # Check file size (should be > 1MB for GGUF models)
        size_mb = self.model_path.stat().st_size / (1024**2)
        if size_mb < 1:
            return False, f"Model file is too small ({size_mb:.2f} MB), may be corrupted"
        
        # Check if file is readable
        try:
            with open(self.model_path, "rb") as f:
                f.read(1024)  # Read first 1KB
            return True, f"Model file verified ({size_mb:.2f} MB)"
        except Exception as e:
            return False, f"Cannot read model file: {e}"

    def detect_model_name(self) -> str | None:
        """Detect model name from path."""
        filename = self.model_path.name
        for model_key in self.MODELS:
            if model_key in filename or filename == model_key:
                return model_key
        return None

    def get_model_info(self, model_name: str | None = None) -> dict[str, Any] | None:
        """Get information about a model."""
        if model_name is None:
            model_name = self.detect_model_name()
        
        if model_name and model_name in self.MODELS:
            return self.MODELS[model_name]
        return None

    def run_checks(self) -> dict[str, Any]:
        """Run all pre-installation checks.
        
        Returns:
            Dictionary with check results
        """
        results = {
            "model_exists": False,
            "model_valid": False,
            "has_disk_space": False,
            "has_download_tool": False,
            "has_internet": False,
            "model_info": None,
            "checks_passed": False,
            "messages": [],
        }

        # Check 1: Model exists
        results["model_exists"] = self.check_model_exists()
        if results["model_exists"]:
            results["messages"].append("[OK] Model file exists")
            # Check 2: Model is valid
            is_valid, msg = self.verify_model_file()
            results["model_valid"] = is_valid
            if is_valid:
                results["messages"].append(f"[OK] {msg}")
            else:
                results["messages"].append(f"[ERROR] {msg}")
        else:
            results["messages"].append(f"[ERROR] Model file not found: {self.model_path}")

        # Get model info
        model_name = self.detect_model_name()
        if model_name:
            results["model_info"] = self.get_model_info(model_name)
            if results["model_info"]:
                results["messages"].append(
                    f"ℹ Model: {results['model_info']['name']} "
                    f"({results['model_info']['size_gb']} GB)"
                )

        # If model doesn't exist, check prerequisites for download
        if not results["model_exists"]:
            # Create directory first (needed for disk space check)
            try:
                self.models_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass  # Will fail later if we can't create it
            
            # Check 3: Disk space
            if results["model_info"]:
                required_gb = results["model_info"]["size_gb"]
                has_space, available_gb, _ = self.check_disk_space(required_gb)
                results["has_disk_space"] = has_space
                if has_space:
                    results["messages"].append(
                        f"[OK] Sufficient disk space ({available_gb:.1f} GB available, "
                        f"{required_gb} GB required)"
                    )
                else:
                    results["messages"].append(
                        f"[ERROR] Insufficient disk space ({available_gb:.1f} GB available, "
                        f"{required_gb} GB required)"
                    )

            # Check 4: Download tool
            has_tool, tool_name = self.check_download_tools()
            results["has_download_tool"] = has_tool
            if has_tool:
                results["messages"].append(f"[OK] Download tool available: {tool_name}")
            else:
                results["messages"].append(
                    "[ERROR] No download tool found (install wget or curl)"
                )

            # Check 5: Internet connection
            results["has_internet"] = self.check_internet_connection()
            if results["has_internet"]:
                results["messages"].append("[OK] Internet connection available")
            else:
                results["messages"].append("[ERROR] No internet connection")

        # Determine if all checks passed
        if results["model_exists"] and results["model_valid"]:
            results["checks_passed"] = True
        elif not results["model_exists"]:
            # For download, need: disk space, download tool, internet
            results["checks_passed"] = (
                results.get("has_disk_space", False)
                and results.get("has_download_tool", False)
                and results.get("has_internet", False)
            )

        return results

    def download_model(self, model_info: dict[str, Any] | None = None) -> bool:
        """Download the model.
        
        Args:
            model_info: Model information dictionary (if None, will detect)
        
        Returns:
            True if successful, False otherwise
        """
        if model_info is None:
            model_name = self.detect_model_name()
            if not model_name:
                logger.error("Could not detect model name from path")
                return False
            model_info = self.get_model_info(model_name)
            if not model_info:
                logger.error(f"Unknown model: {model_name}")
                return False

        # Create models directory first (needed for disk space check and download)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Check download tool
        has_tool, tool_name = self.check_download_tools()
        if not has_tool:
            logger.error("No download tool available (wget or curl required)")
            return False

        url = model_info["url"]
        logger.info(f"Downloading {model_info['name']}...")
        logger.info(f"URL: {url}")
        logger.info(f"Destination: {self.model_path}")
        logger.info(f"Size: ~{model_info['size_gb']} GB")

        # Check if partial download exists (for resume)
        partial_exists = self.model_path.exists()
        if partial_exists:
            size_mb = self.model_path.stat().st_size / (1024**2)
            print(f"ℹ Found partial download ({size_mb:.2f} MB)")
            print("Will resume download...")
            print()

        try:
            if tool_name == "wget":
                # Use wget with progress bar and continue support
                cmd = [
                    "wget",
                    "--continue",  # Resume if interrupted
                    "--progress=bar:force",  # Show progress bar
                    "-O", str(self.model_path),
                    url
                ]
            else:  # curl
                # Use curl with progress bar
                cmd = [
                    "curl",
                    "-L",
                    "--progress-bar",  # Progress bar
                    "--continue-at", "-",  # Resume if interrupted
                    "-o", str(self.model_path),
                    url
                ]

            # Run download with progress
            print("Downloading... (this may take a while)")
            print(f"Model: {model_info['name']}")
            print(f"Size: ~{model_info['size_gb']} GB")
            print(f"Destination: {self.model_path}")
            print()
            print("Progress:")
            print("-" * 60)

            # Run download - let wget/curl show progress directly to stdout/stderr
            process = subprocess.Popen(
                cmd,
                stdout=sys.stdout,
                stderr=sys.stderr,
            )

            # Wait for completion
            try:
                process.wait()
            except KeyboardInterrupt:
                print()
                print("\n⚠ Download interrupted by user")
                process.terminate()
                process.wait()
                if self.model_path.exists():
                    size_mb = self.model_path.stat().st_size / (1024**2)
                    print(f"Partial file saved ({size_mb:.2f} MB)")
                    print("You can resume by running the installer again")
                return False

            print()  # New line after progress
            print("-" * 60)

            if process.returncode == 0:
                print("[OK] Download completed")
                # Verify the downloaded file
                print("Verifying downloaded file...")
                is_valid, msg = self.verify_model_file()
                if is_valid:
                    print(f"[OK] {msg}")
                    logger.info("[OK] Model downloaded and verified successfully")
                    return True
                else:
                    print(f"[ERROR] Download verification failed: {msg}")
                    logger.error(f"[ERROR] Download verification failed: {msg}")
                    # Try to remove invalid file
                    try:
                        if self.model_path.exists():
                            self.model_path.unlink()
                            print("Removed invalid file")
                    except Exception:
                        pass
                    return False
            else:
                error_msg = f"Download failed with return code {process.returncode}"
                print(f"[ERROR] {error_msg}")
                logger.error(error_msg)
                
                # Check if partial file exists
                if self.model_path.exists():
                    size_mb = self.model_path.stat().st_size / (1024**2)
                    print(f"⚠ Partial file exists ({size_mb:.2f} MB)")
                    print("You can resume the download by running the installer again")
                
                return False

        except KeyboardInterrupt:
            print()
            print("\n⚠ Download interrupted by user")
            if self.model_path.exists():
                size_mb = self.model_path.stat().st_size / (1024**2)
                print(f"Partial file saved ({size_mb:.2f} MB)")
                print("You can resume by running the installer again")
            return False
        except Exception as e:
            error_msg = f"Error downloading model: {e}"
            print(f"[ERROR] {error_msg}")
            logger.error(error_msg)
            return False

    def install_model_interactive(self) -> bool:
        """Interactive model installation with checks.
        
        Returns:
            True if model is available (installed or already exists), False otherwise
        """
        print("=" * 70)
        print("Ludus MCP - Model Installation & Verification")
        print("=" * 70)
        print()
        print(f"Model Path: {self.model_path}")
        print()

        # Run checks
        print("Running pre-installation checks...")
        print("-" * 70)
        results = self.run_checks()

        # Display check results
        for message in results["messages"]:
            print(f"  {message}")

        print()
        print("-" * 70)

        # If model exists and is valid, we're done
        if results["model_exists"] and results["model_valid"]:
            print("[OK] Model is ready to use!")
            return True

        # If model doesn't exist, offer to download
        if not results["model_exists"]:
            if not results["checks_passed"]:
                print()
                print("[ERROR] Pre-installation checks failed. Cannot download model.")
                print()
                print("Please fix the following issues:")
                if not results.get("has_disk_space", True):
                    print("  - Free up disk space")
                if not results.get("has_download_tool", False):
                    print("  - Install wget or curl: sudo apt-get install wget")
                if not results.get("has_internet", False):
                    print("  - Check your internet connection")
                return False

            # Offer to download
            if results["model_info"]:
                print()
                print("Model Information:")
                print(f"  Name: {results['model_info']['name']}")
                print(f"  Size: ~{results['model_info']['size_gb']} GB")
                print(f"  Description: {results['model_info']['description']}")
                print()

            if self.interactive:
                response = input("Download and install this model? [Y/n]: ").strip().lower()
                if response == "n":
                    print("Installation cancelled.")
                    return False
            else:
                print("Auto-installing model...")

            print()
            print("Starting download...")
            print("-" * 70)

            if self.download_model(results.get("model_info")):
                print()
                print("=" * 70)
                print("[OK] Model installed successfully!")
                print("=" * 70)
                return True
            else:
                print()
                print("=" * 70)
                print("[ERROR] Model installation failed")
                print("=" * 70)
                return False

        # If model exists but is invalid, offer to re-download
        if results["model_exists"] and not results["model_valid"]:
            print()
            print("⚠ Model file exists but appears to be corrupted or invalid.")
            if self.interactive:
                response = input("Re-download the model? [y/N]: ").strip().lower()
                if response != "y":
                    return False

            # Remove invalid file
            try:
                self.model_path.unlink()
                logger.info("Removed invalid model file")
            except Exception as e:
                logger.error(f"Could not remove invalid file: {e}")
                return False

            # Download again
            return self.download_model(results.get("model_info"))

        return False

