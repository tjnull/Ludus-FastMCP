"""Ludus REST API client wrapper using httpx."""

import asyncio
import httpx
from urllib.parse import quote
import uuid
import time
import yaml
import io
import tarfile
import zipfile
from pathlib import Path
from typing import Any
import logging

from ludus_mcp.utils.config import get_settings
from ludus_mcp.utils.rate_limit import get_rate_limiter
from ludus_mcp.exceptions import (
    LudusAPIError,
    LudusConnectionError,
    LudusAuthenticationError,
    LudusNotFoundError,
    LudusPermissionError,
    LudusServerError,
    LudusTimeoutError,
    LudusRateLimitError,
)

logger = logging.getLogger(__name__)


class LudusAPIClient:
    """Async HTTP client for Ludus API.

    This is the core Ludus API client with no MCP dependencies.
    It provides direct access to the Ludus REST API.
    """

    def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
        """Initialize the Ludus client."""
        settings = get_settings()
        self.base_url = (base_url or settings.ludus_api_url).rstrip("/")
        self.api_key = api_key or settings.ludus_api_key
        self._jwt_token = getattr(settings, "ludus_jwt_token", "") or ""
        self._version_setting = getattr(settings, "ludus_api_version", "auto") or "auto"

        if self._version_setting == "v1":
            raise ValueError(
                "LUDUS_API_VERSION=v1 is no longer supported. This release targets "
                "the Ludus 2.x API only. Upgrade your Ludus server to 2.0 or later, "
                "or pin ludus-fastmcp to a 1.x release for a v1 server."
            )

        # Every endpoint lives under /api/v2; there is no other shape to choose.
        self.api_version = "v2"
        self._base_path = "/api/v2"

        # Populated by verify_server() on the first request: the real Ludus
        # version string, e.g. "2.3.0+02a3ffc8". Setting LUDUS_API_VERSION=v2
        # asserts the server is v2 and skips the verification round-trip.
        self.server_version: str | None = None
        self._server_verified = self._version_setting == "v2"

        # Initialize rate limiter
        self.rate_limiter = get_rate_limiter(max_requests=100, window_seconds=60)

        # Build auth headers - JWT takes precedence over API key
        headers = {}
        if self._jwt_token:
            headers["Authorization"] = f"Bearer {self._jwt_token}"
        elif self.api_key:
            headers["X-API-KEY"] = self.api_key

        self.timeout = float(getattr(settings, "ludus_api_timeout", 120.0))
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            verify=settings.ludus_ssl_verify,
            headers=headers,
            limits=httpx.Limits(
                max_connections=100,
                max_keepalive_connections=20
            )
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self) -> "LudusAPIClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def verify_server(self) -> str:
        """Confirm the server speaks the Ludus 2.x API and record its version.

        GET /api/v2/ returns the server version string on a v2 server. Anything
        else means this client cannot drive it, so fail with an actionable
        message rather than letting every subsequent call 404 in a way that
        looks like a client bug.

        Returns:
            The server version string, e.g. "2.3.0+02a3ffc8".
        """
        try:
            response = await self.client.request(method="GET", url="/api/v2/")
        except httpx.ConnectError as e:
            raise LudusConnectionError(
                f"Cannot connect to Ludus server at {self.base_url}. "
                "Check LUDUS_API_URL and network connectivity."
            ) from e
        except httpx.TimeoutException as e:
            raise LudusTimeoutError(
                f"Timed out contacting {self.base_url} while checking the server version."
            ) from e

        if response.status_code == 401:
            raise LudusAuthenticationError(
                "Authentication failed while checking the server version. "
                "Please check your LUDUS_API_KEY."
            )

        if response.status_code != 200:
            raise LudusAPIError(
                status_code=response.status_code,
                message=(
                    f"{self.base_url} does not serve the Ludus 2.x API "
                    f"(GET /api/v2/ returned HTTP {response.status_code}). "
                    "This release requires Ludus 2.0 or later; upgrade the server, "
                    "or pin ludus-fastmcp to a 1.x release for a Ludus 1.x server."
                ),
                details={"endpoint": "/api/v2/", "method": "GET"},
            )

        version = ""
        try:
            body = response.json()
            if isinstance(body, dict):
                version = str(body.get("version") or "")
        except ValueError:
            pass

        self.server_version = version or "unknown"
        self._server_verified = True
        logger.info(f"Connected to Ludus server {self.server_version}")
        return self.server_version

    async def ensure_server_verified(self) -> str:
        """Verify the server once, on the first call that needs it.

        Verification is lazy so constructing a client never performs I/O.
        """
        if not self._server_verified:
            await self.verify_server()
        return self.server_version or "unknown"

    # A connection error means the request never reached the server, so replaying
    # it is safe for any method. A timeout means it may already have been acted
    # on, so only methods without side effects are replayed - retrying a timed-out
    # POST /range/deploy would risk deploying twice.
    _RETRY_MAX_ATTEMPTS = 3
    _RETRY_INITIAL_DELAY = 1.0
    _RETRY_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

    @staticmethod
    def _path(value: Any) -> str:
        """Percent-encode a value for use as a single URL path segment.

        Source-installed IDs contain slashes ("ludus-source-bsl/goad"), which
        interpolated raw turn one path segment into two and 404. Group and
        template names can likewise contain characters that need escaping.
        """
        return quote(str(value), safe="")

    async def _request(
        self,
        method: str,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        raw: bool = False,
    ) -> dict[str, Any] | list[Any]:
        """Make an HTTP request to the Ludus API with retry logic and error handling.

        Args:
            files/data: multipart form-data parts, for endpoints that upload archives.
            raw: return the undecoded body instead of parsing JSON, for endpoints that
                serve gzip/YAML/HTML rather than JSON.
        """
        # Lazy version detection on first API call
        if not self._server_verified:
            await self.verify_server()

        delay = self._RETRY_INITIAL_DELAY

        for attempt in range(1, self._RETRY_MAX_ATTEMPTS + 1):
            try:
                return await self._send_request(
                    method, endpoint, json_data, params, files, data, raw
                )
            except (LudusConnectionError, LudusTimeoutError) as e:
                retryable = isinstance(e, LudusConnectionError) or (
                    method.upper() in self._RETRY_SAFE_METHODS
                )
                if not retryable or attempt == self._RETRY_MAX_ATTEMPTS:
                    raise

                logger.warning(
                    f"{method} {endpoint} failed with {type(e).__name__} "
                    f"(attempt {attempt}/{self._RETRY_MAX_ATTEMPTS}). "
                    f"Retrying in {delay:.1f}s..."
                )
                await asyncio.sleep(delay)
                delay *= 2

    async def _send_request(
        self,
        method: str,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        raw: bool = False,
    ) -> dict[str, Any] | list[Any]:
        """Perform a single HTTP request attempt, mapping errors to Ludus exceptions."""
        # Generate request ID for tracing
        request_id = str(uuid.uuid4())[:8]

        # Apply rate limiting
        await self.rate_limiter.acquire()

        # Log request (debug level)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"[{request_id}] → {method} {endpoint}")
            if json_data:
                logger.debug(f"[{request_id}] Request body: {json_data}")

        start_time = time.time()

        try:
            # Ludus API uses X-API-KEY header (already set in client)
            # Just add Content-Type if needed
            headers = {}
            if json_data:
                headers["Content-Type"] = "application/json"

            response = await self.client.request(
                method=method,
                url=f"{self._base_path}{endpoint}",
                json=json_data,
                params=params,
                headers=headers,
                files=files,
                data=data,
            )

            duration = time.time() - start_time

            # Log response (debug level)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    f"[{request_id}] ← {response.status_code} ({duration:.2f}s)"
                )
                if response.content:
                    content_preview = response.text[:500]
                    logger.debug(f"[{request_id}] Response: {content_preview}")

            response.raise_for_status()

            if not response.content:
                return {}

            content_type = response.headers.get("content-type", "")

            if raw:
                return {
                    "content_type": content_type,
                    "size_bytes": len(response.content),
                    "content": response.content,
                }

            try:
                return response.json()
            except ValueError:
                # Some endpoints advertise JSON but serve YAML/HTML/plain text
                # (e.g. /openapi). Hand back the body rather than exploding.
                logger.debug(
                    f"[{request_id}] Response was not JSON (content-type: {content_type})"
                )
                return {
                    "content_type": content_type,
                    "size_bytes": len(response.content),
                    "text": response.text,
                }

        except httpx.TimeoutException as e:
            logger.error(f"[{request_id}] [ERROR] Request timed out after {time.time() - start_time:.2f}s")
            raise LudusTimeoutError(
                f"Request to {endpoint} timed out after {self.timeout:g} seconds. "
                "The server may still be processing it - check state before retrying. "
                "Raise LUDUS_API_TIMEOUT if this operation is legitimately slow."
            ) from e

        except httpx.ConnectError as e:
            logger.error(f"[{request_id}] [ERROR] Connection failed: {e}")
            raise LudusConnectionError(
                f"Cannot connect to Ludus server at {self.base_url}. "
                f"Please check your LUDUS_API_URL and network connectivity."
            ) from e

        except httpx.NetworkError as e:
            logger.error(f"[{request_id}] [ERROR] Network error: {e}")
            raise LudusConnectionError(
                f"Network error connecting to {self.base_url}: {e}"
            ) from e

        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            error_text = e.response.text[:200] if e.response.text else "No error details"

            # Ludus reports failures as {"error": "..."}. That message distinguishes
            # cases the status code alone cannot -- most importantly a 404 meaning
            # "this endpoint lives in an unloaded plugin" from a 404 meaning "wrong
            # URL". Collapsing them sends callers hunting for a bug that isn't there.
            server_message = ""
            try:
                body = e.response.json()
                if isinstance(body, dict):
                    server_message = str(body.get("error") or body.get("message") or "")
            except ValueError:
                pass

            logger.error(f"[{request_id}] [ERROR] HTTP {status}: {error_text}")

            detail = f" Server said: {server_message}" if server_message else ""

            if status == 401:
                raise LudusAuthenticationError(
                    f"Authentication failed. Please check your LUDUS_API_KEY.{detail}"
                ) from e
            elif status == 403:
                raise LudusPermissionError(
                    f"Permission denied for {endpoint}. "
                    f"You may not have the required admin privileges.{detail}"
                ) from e
            elif status == 404:
                if "plugin" in server_message.lower():
                    raise LudusNotFoundError(
                        f"{endpoint} is not available on this Ludus server: "
                        f"{server_message}. This endpoint is provided by a plugin "
                        "(typically an enterprise feature) that is not loaded. "
                        "The request was correct -- the capability is absent. Do not "
                        "retry with a different path."
                    ) from e
                raise LudusNotFoundError(
                    f"Resource not found: {endpoint}.{detail}"
                ) from e
            elif status == 429:
                retry_after = e.response.headers.get("Retry-After")
                raise LudusRateLimitError(
                    retry_after=int(retry_after) if retry_after else None
                ) from e
            elif status == 501:
                # Permanent: this build does not implement the endpoint at all.
                # "Try again later" would send the caller into a pointless loop.
                raise LudusNotFoundError(
                    f"{endpoint} is not implemented by this Ludus server "
                    f"(HTTP 501).{detail} Retrying will not help -- this build "
                    "does not provide the feature."
                ) from e
            elif status >= 500:
                raise LudusServerError(
                    f"Ludus API server error ({status}).{detail} Please try again later."
                ) from e
            else:
                raise LudusAPIError(
                    status_code=status,
                    message=error_text,
                    details={"endpoint": endpoint, "method": method}
                ) from e

    # Range operations
    # Note: Ludus API uses /range/config for range configuration
    # Ranges are deployed via POST /range/deploy with a config
    async def get_range(self, user_id: str | None = None) -> dict[str, Any]:
        """Get the current user's range."""
        params = {}
        if user_id:
            params["userID"] = user_id
        return await self._request("GET", "/range", params=params)

    async def list_ranges(self) -> list[dict[str, Any]]:
        """List all ranges (admin only)."""
        result = await self._request("GET", "/range/all")
        return result if isinstance(result, list) else []

    async def delete_range(self, user_id: str | None = None, require_explicit_user: bool = True) -> dict[str, Any]:
        """Destroy every VM in a range, keeping the range object itself.

        This is the equivalent of `ludus range rm`: the VMs and their snapshots
        are gone, but the range and its configuration survive, so it can be
        redeployed. Use delete_range_object() to remove the range entirely.

        **CRITICAL SAFETY**: This function will ONLY affect the range for the
        specified user_id. It will NEVER touch other users' ranges or system
        settings.

        Args:
            user_id: User ID whose range to wipe. If None, defaults to current API key's user.
            require_explicit_user: If True (default), requires user_id to be explicitly provided.
                                  Set to False only if you're certain you want to wipe the current user's range.

        Raises:
            ValueError: If require_explicit_user=True and user_id is None (safety check)
        """
        # CRITICAL SAFETY CHECK: Prevent accidental system-wide operations
        if require_explicit_user and user_id is None:
            raise ValueError(
                "SAFETY CHECK FAILED: delete_range() requires explicit user_id to prevent accidental deletions. "
                "If you want to delete the current user's range, pass user_id explicitly or set require_explicit_user=False. "
                "This safeguard prevents accidental deletion of other users' ranges or system settings."
            )
        
        # Get current user from API key to ensure we're only deleting our own range
        current_user_id = None
        try:
            current_user_info = await self.get_user()
            current_user_id = current_user_info.get("userID") or current_user_info.get("user_id")
            logger.info(f"[SAFETY] Current API key user: {current_user_id}")
        except Exception as e:
            logger.warning(f"[SAFETY] Could not verify current user (this is OK): {e}")
        
        # Use explicit user_id if provided, otherwise use current user
        target_user_id = user_id or current_user_id
        
        if not target_user_id:
            raise ValueError(
                "SAFETY CHECK FAILED: Cannot determine target user for range deletion. "
                "Please provide user_id explicitly."
            )
        
        # Log the deletion operation for audit trail
        logger.warning(
            f"[DESTRUCTIVE OPERATION] Deleting range for user: {target_user_id}. "
            f"This will permanently delete all VMs, snapshots, and data for this user's range only."
        )
        
        params = {}
        if target_user_id:
            params["userID"] = target_user_id
            logger.info(f"[SAFETY] Using explicit userID parameter: {target_user_id}")

        range_info = await self.get_range(user_id=target_user_id)
        range_id = range_info.get("rangeID", range_info.get("range_id", ""))
        if not range_id:
            raise ValueError("Could not determine rangeID for VM deletion")
        return await self._request("DELETE", f"/range/{self._path(range_id)}/vms", params=params)

    async def delete_range_object(
        self,
        user_id: str | None = None,
        range_id: str | None = None,
        force: bool = False,
        require_explicit_user: bool = True,
    ) -> dict[str, Any]:
        """Delete a range from the database and Proxmox entirely.

        This is `ludus range rm-range`, not `ludus range rm`: it removes the
        range object itself, so the configuration is gone too. Use delete_range()
        to wipe only the VMs and keep the range for redeployment.

        The API refuses to delete a range that still has VMs unless force is set.

        Args:
            user_id: Owner of the range. Required unless require_explicit_user is False.
            range_id: Range to delete. Defaults to the user's default range.
            force: Destroy any remaining VMs as part of the deletion.
            require_explicit_user: Safety check; see delete_range().

        Raises:
            ValueError: If require_explicit_user=True and user_id is None
        """
        if require_explicit_user and user_id is None:
            raise ValueError(
                "SAFETY CHECK FAILED: delete_range_object() requires an explicit user_id. "
                "This removes the range object itself, not just its VMs. Pass user_id "
                "explicitly, or set require_explicit_user=False for your own range."
            )

        logger.critical(
            f"[DESTRUCTIVE OPERATION] Deleting the range OBJECT for user: "
            f"{user_id or 'current user'} (range: {range_id or 'default'}). "
            "The range and its configuration are removed, not just the VMs."
        )

        params: dict[str, Any] = {}
        if user_id:
            params["userID"] = user_id
        if range_id:
            params["rangeID"] = range_id
        if force:
            params["force"] = "true"

        return await self._request("DELETE", "/range", params=params)

    async def get_range_config(self, user_id: str | None = None) -> dict[str, Any]:
        """Get range configuration.
        
        The Ludus API returns the configuration as a YAML string in the 'result' field.
        This method parses the YAML string into a dictionary.
        """
        params = {}
        if user_id:
            params["userID"] = user_id
        result = await self._request("GET", "/range/config", params=params)
        
        # Ludus API returns YAML as a string in the 'result' field
        if isinstance(result, dict) and "result" in result:
            yaml_str = result["result"]
            if isinstance(yaml_str, str):
                return yaml.safe_load(yaml_str) or {}
        
        return result if isinstance(result, dict) else {}

    async def update_range_config(
        self, config: dict[str, Any], user_id: str | None = None
    ) -> dict[str, Any]:
        """Update range configuration.
        
        The Ludus API requires the configuration to be sent as a YAML file via multipart/form-data.
        This method converts the config dict to YAML and sends it as a file upload.
        """
        # This method builds its own URL from _base_path and bypasses _request(),
        # so the lazy detection there never runs: without this, a first-call
        # upload goes to /range/config instead of /api/v2/range/config and 404s.
        await self.ensure_server_verified()

        params = {}
        if user_id:
            params["userID"] = user_id
        
        # Remove 'name' field if present - Ludus API doesn't accept it in config
        config_copy = config.copy()
        if "name" in config_copy:
            del config_copy["name"]
        
        # Convert config to YAML string
        yaml_str = yaml.dump(config_copy, default_flow_style=False, sort_keys=False)
        
        # Create multipart form data with YAML file
        files = {
            "file": ("config.yml", io.BytesIO(yaml_str.encode("utf-8")), "application/x-yaml")
        }
        
        # Make request with multipart form data
        request_id = str(uuid.uuid4())[:8]
        await self.rate_limiter.acquire()
        
        try:
            response = await self.client.request(
                method="PUT",
                url=f"{self._base_path}/range/config",
                params=params,
                files=files,
            )
            
            response.raise_for_status()
            
            if response.content:
                return response.json()
            return {}
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            error_text = e.response.text[:200] if e.response.text else "No error details"
            
            logger.error(f"[{request_id}] [ERROR] HTTP {status}: {error_text}")
            
            if status == 401:
                raise LudusAuthenticationError(
                    "Authentication failed. Please check your LUDUS_API_KEY."
                ) from e
            elif status >= 500:
                raise LudusServerError(
                    f"Ludus API server error ({status}). Please try again later."
                ) from e
            else:
                raise LudusAPIError(
                    status_code=status,
                    message=error_text,
                    details={"endpoint": "/range/config", "method": "PUT"}
                ) from e

    async def deploy_range(
        self,
        config: dict[str, Any] | None = None,
        user_id: str | None = None,
        tags: str | None = None,
        limit: str | None = None,
        only_roles: str | None = None,
        force: bool = False,
        range_id: str | None = None,
    ) -> dict[str, Any]:
        """Deploy a range.

        The deploy filters go in the request BODY; only rangeID and userID are
        query parameters. Sending tags/limit/force as query parameters gets them
        silently ignored, so a request meant to touch one VM redeploys the
        entire range instead.

        Args:
            config: Range configuration. If given it is stored first, since the
                deploy endpoint itself deploys whatever config is already saved.
            user_id: User ID for admin impersonation
            tags: Ansible tags to run (comma-separated, e.g., "user,domain")
            limit: Limit deployment to VMs matching pattern (e.g., "DC*")
            only_roles: Limit user-defined roles (comma-separated)
            force: Force deployment if testing is enabled
            range_id: Range to deploy. Defaults to the user's default range.

        Returns:
            Deployment result

        Examples:
            # Full deployment
            deploy_range(config=config_dict)

            # Resume with specific tags (e.g., after role installation)
            deploy_range(tags="user,domain")

            # Deploy only to specific VMs
            deploy_range(limit="DC*")

            # Combine filters
            deploy_range(tags="user", limit="WS*")
        """
        # /range/deploy has no config field -- it deploys the stored config. Store
        # it first so deploy_range(config=...) behaves the way it reads.
        if config is not None:
            await self.update_range_config(config, user_id)

        params: dict[str, Any] = {}
        if user_id:
            params["userID"] = user_id
        if range_id:
            params["rangeID"] = range_id

        payload: dict[str, Any] = {}
        if tags:
            payload["tags"] = tags
        if limit:
            payload["limit"] = limit
        if only_roles:
            payload["only_roles"] = only_roles
        if force:
            payload["force"] = True

        return await self._request(
            "POST", "/range/deploy", json_data=payload or None, params=params
        )

    # Range Management - Additional endpoints
    async def abort_range_deployment(self, user_id: str | None = None, require_explicit_user: bool = True) -> dict[str, Any]:
        """Abort a range deployment.
        
        **CRITICAL SAFETY**: This function will ONLY abort the deployment for the specified user_id.
        It will NEVER affect other users' deployments or system settings.
        
        Args:
            user_id: User ID whose deployment to abort. If None, defaults to current API key's user.
            require_explicit_user: If True (default), requires user_id to be explicitly provided.
        
        Raises:
            ValueError: If require_explicit_user=True and user_id is None (safety check)
        """
        # CRITICAL SAFETY CHECK: Prevent accidental system-wide operations
        if require_explicit_user and user_id is None:
            # Get current user from API key
            try:
                current_user_info = await self.get_user()
                user_id = current_user_info.get("userID") or current_user_info.get("user_id")
                if user_id:
                    logger.info(f"[SAFETY] Using current API key user for abort: {user_id}")
                else:
                    raise ValueError(
                        "SAFETY CHECK FAILED: abort_range_deployment() requires explicit user_id. "
                        "Cannot determine current user from API key."
                    )
            except Exception as e:
                raise ValueError(
                    f"SAFETY CHECK FAILED: abort_range_deployment() requires explicit user_id. "
                    f"Could not determine current user: {e}"
                )
        
        params = {}
        if user_id:
            params["userID"] = user_id
            logger.info(f"[SAFETY] Aborting deployment for user: {user_id}")
        return await self._request("POST", "/range/abort", params=params)

    async def get_range_tags(self) -> list[str]:
        """Get range tags."""
        result = await self._request("GET", "/range/tags")
        return result if isinstance(result, list) else []

    async def get_range_config_example(self) -> dict[str, Any]:
        """Get example range configuration."""
        return await self._request("GET", "/range/config/example")

    async def get_range_logs(
        self, user_id: str | None = None, tail: int | None = None
    ) -> str:
        """Get range deployment logs.

        Args:
            user_id: Optional user ID (admin only)
            tail: Only return the last N lines. Deployment logs run to tens of
                thousands of lines, so callers should almost always set this.
        """
        params: dict[str, Any] = {}
        if user_id:
            params["userID"] = user_id
        if tail is not None:
            params["tail"] = tail
        result = await self._request("GET", "/range/logs", params=params)
        return result.get("result", "") if isinstance(result, dict) else str(result)

    async def get_range_etchosts(self, user_id: str | None = None) -> str:
        """Get /etc/hosts file for the range."""
        params = {}
        if user_id:
            params["userID"] = user_id
        result = await self._request("GET", "/range/etchosts", params=params)
        return result.get("result", "") if isinstance(result, dict) else str(result)

    async def get_range_sshconfig(self, user_id: str | None = None) -> str:
        """Get SSH config for the range."""
        params = {}
        if user_id:
            params["userID"] = user_id
        result = await self._request("GET", "/range/sshconfig", params=params)
        return result.get("result", "") if isinstance(result, dict) else str(result)

    async def get_range_rdpconfigs(self, user_id: str | None = None) -> dict[str, Any]:
        """Get RDP configurations for the range.

        This endpoint answers with a ZIP archive, not JSON. Parsing it as JSON
        failed with "'utf-8' codec can't decode byte 0x81". The archive is
        unpacked here so callers get the .rdp files as text.
        """
        await self.ensure_server_verified()

        params = {}
        if user_id:
            params["userID"] = user_id

        await self.rate_limiter.acquire()
        response = await self.client.request(
            method="GET", url=f"{self._base_path}/range/rdpconfigs", params=params
        )
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "json" in content_type:
            return response.json()

        files: dict[str, str] = {}
        try:
            with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                for name in archive.namelist():
                    if name.endswith("/"):
                        continue
                    files[name] = archive.read(name).decode("utf-8", errors="replace")
        except zipfile.BadZipFile:
            return {
                "content_type": content_type,
                "size_bytes": len(response.content),
                "error": "Response was not JSON or a readable ZIP archive.",
            }

        return {"count": len(files), "files": files, "content_type": content_type}

    async def get_range_ansible_inventory(self, user_id: str | None = None) -> str:
        """Get Ansible inventory for the range."""
        params = {}
        if user_id:
            params["userID"] = user_id
        result = await self._request("GET", "/range/ansibleinventory", params=params)
        return result.get("result", "") if isinstance(result, dict) else str(result)

    async def get_range_access(self, user_id: str | None = None) -> dict[str, Any]:
        """Get range access configuration."""
        return await self._request("GET", "/ranges/accessible")

    async def update_range_access(
        self, access_config: dict[str, Any], user_id: str | None = None
    ) -> dict[str, Any]:
        """Update range access configuration."""
        target_user = access_config.get("userID", user_id)
        range_id = access_config.get("rangeID", "")
        if not (target_user and range_id):
            raise ValueError(
                "Granting range access requires both userID and rangeID. "
                "Access is assigned per (user, range) pair."
            )
        return await self._request(
            "POST", f"/ranges/assign/{self._path(target_user)}/{self._path(range_id)}"
        )

    # Power State Management
    @staticmethod
    def _machine_list(vms: str | list[str] | None) -> list[str]:
        """Normalise a VM selector into the API's "machines" array."""
        if vms is None:
            return ["all"]
        if isinstance(vms, str):
            if vms.strip().lower() == "all":
                return ["all"]
            return [part.strip() for part in vms.split(",") if part.strip()] or ["all"]
        return [str(v) for v in vms] or ["all"]

    async def power_on_range(self, user_id: str | None = None, vms: str = "all") -> dict[str, Any]:
        """Power on VMs in the range.

        Args:
            user_id: Optional user ID (admin only)
            vms: VM names (comma-separated) or 'all' (default). Required for v2.
        """
        params = {}
        if user_id:
            params["userID"] = user_id
        # The API takes a JSON body with a "machines" ARRAY. Sending "vms" as a
        # query parameter left the selector empty and the server answered 409
        # "you must specify a VM, comma separated list of VMs, or 'all'".
        machines = self._machine_list(vms)
        return await self._request(
            "PUT", "/range/poweron", json_data={"machines": machines}, params=params
        )

    async def power_off_range(self, user_id: str | None = None, vms: str = "all") -> dict[str, Any]:
        """Power off VMs in the range.

        Args:
            user_id: Optional user ID (admin only)
            vms: VM names (comma-separated) or 'all' (default). Required for v2.
        """
        params = {}
        if user_id:
            params["userID"] = user_id
        # The API takes a JSON body with a "machines" ARRAY. Sending "vms" as a
        # query parameter left the selector empty and the server answered 409
        # "you must specify a VM, comma separated list of VMs, or 'all'".
        machines = self._machine_list(vms)
        return await self._request(
            "PUT", "/range/poweroff", json_data={"machines": machines}, params=params
        )

    # Testing State Management
    async def start_testing(self, user_id: str | None = None) -> dict[str, Any]:
        """Start testing state for the range."""
        params = {}
        if user_id:
            params["userID"] = user_id
        return await self._request("PUT", "/testing/start", params=params)

    async def stop_testing(self, user_id: str | None = None) -> dict[str, Any]:
        """Stop testing state for the range."""
        params = {}
        if user_id:
            params["userID"] = user_id
        return await self._request("PUT", "/testing/stop", params=params)

    async def allow_testing(
        self, allowed_config: dict[str, Any], user_id: str | None = None
    ) -> dict[str, Any]:
        """Allow testing from specific IPs/domains."""
        params = {}
        if user_id:
            params["userID"] = user_id
        return await self._request("POST", "/testing/allow", json_data=allowed_config, params=params)

    async def deny_testing(
        self, denied_config: dict[str, Any], user_id: str | None = None
    ) -> dict[str, Any]:
        """Deny testing from specific IPs/domains."""
        params = {}
        if user_id:
            params["userID"] = user_id
        return await self._request("POST", "/testing/deny", json_data=denied_config, params=params)

    async def update_testing(
        self, testing_config: dict[str, Any], user_id: str | None = None
    ) -> dict[str, Any]:
        """Update testing configuration."""
        params = {}
        if user_id:
            params["userID"] = user_id
        return await self._request("POST", "/testing/update", json_data=testing_config, params=params)

    # Snapshot Management (Ludus API format)
    async def list_snapshots(self, user_id: str | None = None) -> list[dict[str, Any]]:
        """List all snapshots for the range."""
        params = {}
        if user_id:
            params["userID"] = user_id
        result = await self._request("GET", "/snapshots/list", params=params)
        # The API wraps the list: {"snapshots": [...]}. Treating a non-list as
        # empty silently reported "no snapshots" for every range that had them.
        if isinstance(result, dict):
            return result.get("snapshots") or []
        return result if isinstance(result, list) else []

    async def resolve_vm_ids(
        self, vm_names: str | list[str] | None, user_id: str | None = None
    ) -> list[int]:
        """Translate VM names into Proxmox VMIDs for the snapshot endpoints.

        The snapshot API selects machines by "vmids", not by name; passing a
        name field it does not understand silently applies the operation to
        EVERY VM in the range.

        Args:
            vm_names: One name, several names, or None for the whole range
            user_id: Optional user ID (admin only)

        Returns:
            Matching VMIDs; empty list means "all VMs in the range"

        Raises:
            ValueError: If a requested name is not in the range.
        """
        if not vm_names:
            return []

        names = [vm_names] if isinstance(vm_names, str) else list(vm_names)
        range_info = await self.get_range(user_id)
        vms = range_info.get("VMs", []) or []
        by_name = {vm.get("name"): vm.get("proxmoxID") for vm in vms}

        vmids: list[int] = []
        missing: list[str] = []
        for name in names:
            vmid = by_name.get(name)
            if vmid is None:
                missing.append(name)
            else:
                vmids.append(int(vmid))

        if missing:
            raise ValueError(
                f"VM(s) not found in range: {', '.join(missing)}. "
                f"Available: {', '.join(n for n in by_name if n) or 'none'}"
            )
        return vmids

    async def create_snapshot(
        self,
        snapshot_config: dict[str, Any],
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a snapshot."""
        params = {}
        if user_id:
            params["userID"] = user_id
        return await self._request("POST", "/snapshots/create", json_data=snapshot_config, params=params)

    async def rollback_snapshot(
        self,
        snapshot_config: dict[str, Any],
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Rollback to a snapshot."""
        params = {}
        if user_id:
            params["userID"] = user_id
        return await self._request("POST", "/snapshots/rollback", json_data=snapshot_config, params=params)

    async def remove_snapshot(
        self,
        snapshot_config: dict[str, Any],
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Remove a snapshot."""
        params = {}
        if user_id:
            params["userID"] = user_id
        return await self._request("POST", "/snapshots/remove", json_data=snapshot_config, params=params)

    # Template Management
    async def list_templates(self) -> list[dict[str, Any]]:
        """List available templates."""
        result = await self._request("GET", "/templates")
        return result if isinstance(result, list) else []

    async def create_template(
        self, template_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a new template."""
        return await self._request("POST", "/templates", json_data=template_config)

    async def update_template(
        self, template_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Update a template."""
        return await self._request("PUT", "/templates", json_data=template_config)

    async def delete_template(self, template_name: str, user_id: str | None = None) -> dict[str, Any]:
        """Delete a template."""
        params = {}
        if user_id:
            params["userID"] = user_id
        return await self._request("DELETE", f"/template/{self._path(template_name)}", params=params)

    async def abort_template_operation(self, user_id: str | None = None) -> dict[str, Any]:
        """Abort template operation."""
        params = {}
        if user_id:
            params["userID"] = user_id
        return await self._request("POST", "/templates/abort", params=params)

    async def get_template_logs(self, user_id: str | None = None, tail: int | None = None) -> str:
        """Get template operation logs."""
        params = {}
        if user_id:
            params["userID"] = user_id
        if tail is not None:
            params["tail"] = tail
        result = await self._request("GET", "/templates/logs", params=params)
        return result.get("result", "") if isinstance(result, dict) else str(result)

    async def get_template_status(self, user_id: str | None = None) -> dict[str, Any]:
        """Get template operation status."""
        params = {}
        if user_id:
            params["userID"] = user_id
        result = await self._request("GET", "/templates/status", params=params)
        # The API answers `null` when no build is running; returning None made
        # the MCP tool fail output validation ("outputSchema defined but no
        # structured output"). Report an explicit, empty status instead.
        if result is None:
            return {"building": [], "status": "idle"}
        if isinstance(result, list):
            return {"building": result, "status": "building" if result else "idle"}
        return result

    async def add_template(
        self,
        directory: str,
        force: bool = False,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Add a packer template to Ludus by uploading a local directory.

        Ludus has no URL-based template add: templates are packer directories
        uploaded as a gzipped tar. The endpoint is PUT /templates; the older
        POST /templates/add path does not exist and returns 404.

        Args:
            directory: Local template directory. Windows templates must contain
                an Autounattend.xml at their root.
            force: Replace the template directory if it already exists on Ludus.
            user_id: Optional user ID (admin only)

        Returns:
            API response with template add status
        """
        path = Path(directory)
        if not path.is_dir():
            raise ValueError(
                f"Template directory not found: {directory}. "
                "add_template uploads a local packer template directory."
            )

        # The endpoint reads a plain tar; a gzipped one is rejected with
        # "Invalid tar archive: unexpected EOF".
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w") as tar:
            tar.add(str(path), arcname=path.name)

        files = {"file": (f"{path.name}.tar", buffer.getvalue(), "application/x-tar")}
        data = {"force": str(force).lower()}

        params = {}
        if user_id:
            params["userID"] = user_id

        return await self._request("PUT", "/templates", files=files, data=data, params=params)

    async def build_template(
        self,
        template_name: str | list[str] | None = None,
        parallel: int = 1,
        user_id: str | None = None
    ) -> dict[str, Any]:
        """Build one template, several templates, or all of them.

        Args:
            template_name: Template name, list of names, or None for all templates
            parallel: Number of templates to build in parallel (default: 1)
            user_id: Optional user ID (admin only)

        Returns:
            API response with build status
        """
        payload: dict[str, Any] = {"parallel": parallel}

        if template_name:
            names = [template_name] if isinstance(template_name, str) else list(template_name)
            payload["templates"] = names

        params = {}
        if user_id:
            params["userID"] = user_id

        return await self._request("POST", "/templates", json_data=payload, params=params)

    # Host Management
    async def get_host_info(self) -> dict[str, Any]:
        """Get Ludus host information."""
        return await self._request("GET", "/")

    # Ansible Management
    async def list_ansible_resources(self) -> dict[str, Any]:
        """List Ansible roles and collections."""
        return await self._request("GET", "/ansible")

    async def install_ansible_role(
        self, role_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Install an Ansible role.

        Args:
            role_config: Role configuration dict with:
                - "role" (or "name"): role name, e.g. "geerlingguy.java"
                - "action": "install" (default)
                - "version": optional version to pin
                - "force": optional, reinstall if already present
                - "global": optional, install for all users (admin only)
                - "directory": optional path on the SERVER for a local install
        """
        payload = dict(role_config)

        # The API field is "role"; callers historically passed "name", which the
        # server read as an empty role name and answered
        # "sorry, '' was not found on https://galaxy.ansible.com/api/".
        if "role" not in payload:
            name = payload.pop("name", None)
            if name:
                payload["role"] = name
        else:
            payload.pop("name", None)

        if not payload.get("role") and not payload.get("directory"):
            raise ValueError(
                "install_ansible_role() needs a role name (or a directory to install from)."
            )

        payload.setdefault("action", "install")
        return await self._request("POST", "/ansible/role", json_data=payload)

    async def install_ansible_role_from_tar(
        self, role_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Install an Ansible role from tar file."""
        return await self._request("PUT", "/ansible/role/fromtar", json_data=role_config)

    async def install_ansible_collection(
        self, collection_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Install an Ansible collection."""
        return await self._request("POST", "/ansible/collection", json_data=collection_config)

    # Anti-Sandbox Management
    async def enable_antisandbox(
        self, config: dict[str, Any], user_id: str | None = None
    ) -> dict[str, Any]:
        """Enable anti-sandbox plugin."""
        params = {}
        if user_id:
            params["userID"] = user_id
        return await self._request("POST", "/antisandbox/enable", json_data=config, params=params)

    async def install_antisandbox_custom(
        self, config: dict[str, Any], user_id: str | None = None
    ) -> dict[str, Any]:
        """Install custom anti-sandbox plugin."""
        params = {}
        if user_id:
            params["userID"] = user_id
        return await self._request("POST", "/antisandbox/install-custom", json_data=config, params=params)

    async def install_antisandbox_standard(
        self, user_id: str | None = None
    ) -> dict[str, Any]:
        """Install standard anti-sandbox plugin."""
        params = {}
        if user_id:
            params["userID"] = user_id
        return await self._request("POST", "/antisandbox/install-standard", params=params)

    # KMS Management
    async def install_kms(
        self, config: dict[str, Any], user_id: str | None = None
    ) -> dict[str, Any]:
        """Install Key Management Service."""
        params = {}
        if user_id:
            params["userID"] = user_id
        return await self._request("POST", "/kms/install", json_data=config, params=params)

    async def license_kms(
        self, config: dict[str, Any], user_id: str | None = None
    ) -> dict[str, Any]:
        """License KMS server."""
        params = {}
        if user_id:
            params["userID"] = user_id
        return await self._request("POST", "/kms/license", json_data=config, params=params)

    # User Management (Admin only)
    async def list_users(self) -> list[dict[str, Any]]:
        """List all users (admin only)."""
        result = await self._request("GET", "/user/all")
        return result if isinstance(result, list) else []

    async def get_user(self, user_id: str | None = None) -> dict[str, Any]:
        """Get user information.
        
        Args:
            user_id: Optional user ID (defaults to caller's user if not specified)
                    Use query parameter userID, not path parameter
        """
        params = {}
        if user_id:
            params["userID"] = user_id
        result = await self._request("GET", "/user", params=params)
        # The API answers with a single-element list even when asked for one
        # user; unwrap it so this matches its declared dict return type (and so
        # the MCP tool does not fail structured-output validation).
        if isinstance(result, list):
            return result[0] if result else {}
        return result

    async def add_user(
        self,
        user_id: str,
        name: str,
        is_admin: bool = False,
        proxmox_username: str | None = None,
        proxmox_password: str | None = None,
        email: str | None = None,
    ) -> dict[str, Any]:
        """Add a new user (admin only).

        Args:
            user_id: User ID (1-20 character alphanumeric)
            name: User's full name
            is_admin: Whether user is an admin
            proxmox_username: Optional Proxmox username
            proxmox_password: Optional Proxmox password
            email: Optional email address (v2 only)
        """
        # The API rejects user creation without an email ("Email is required"),
        # so fail here with something actionable instead of a raw 400.
        if not email:
            raise ValueError(
                f"Ludus 2.0+ requires an email address to create user '{user_id}'. "
                "Pass email=... (Ludus uses <userid>@ludus.internal by convention)."
            )

        payload: dict[str, Any] = {
            "userID": user_id,
            "name": name,
            "isAdmin": is_admin,
        }
        if proxmox_username:
            payload["proxmoxUsername"] = proxmox_username
        if proxmox_password:
            payload["proxmoxPassword"] = proxmox_password
        if email:
            payload["email"] = email

        return await self._request("POST", "/user", json_data=payload)

    async def remove_user(
        self, user_id: str, require_confirmation: bool = True, delete_default_range: bool = False
    ) -> dict[str, Any]:
        """Remove a user (admin only).

        **CRITICAL SAFETY**: This function permanently deletes a user and all their data.
        This operation CANNOT be undone.

        Args:
            user_id: User ID to remove
            require_confirmation: If True (default), raises ValueError if user_id is empty or looks like a wildcard.
            delete_default_range: If True (v2 only), also delete the user's default range.

        Raises:
            ValueError: If require_confirmation=True and user_id appears unsafe (empty, wildcard, etc.)
        """
        # CRITICAL SAFETY CHECK: Prevent accidental deletion of all users
        if require_confirmation:
            if not user_id or not user_id.strip():
                raise ValueError(
                    "SAFETY CHECK FAILED: remove_user() requires a non-empty user_id. "
                    "This prevents accidental deletion of all users."
                )
            if user_id in ["*", "all", "ALL", "%", "?"]:
                raise ValueError(
                    f"SAFETY CHECK FAILED: remove_user() does not accept wildcard user_id '{user_id}'. "
                    "This prevents accidental deletion of multiple users. "
                    "You must specify an exact user_id."
                )

        logger.critical(
            f"[DESTRUCTIVE OPERATION] Removing user: {user_id}. "
            f"This will permanently delete the user, their API keys, ranges, and all associated data. "
            f"This operation CANNOT be undone."
        )

        params = {}
        if delete_default_range:
            params["deleteDefaultRange"] = "true"
        return await self._request("DELETE", f"/user/{self._path(user_id)}", params=params)

    # Blueprint Management (v2 only)
    async def list_blueprints(
        self, from_source: str | None = None, tag: str | None = None
    ) -> list[dict[str, Any]]:
        """List all blueprints, optionally filtered by source or tag."""
        params = {}
        if from_source:
            params["from-source"] = from_source
        if tag:
            params["tag"] = tag
        result = await self._request("GET", "/blueprints", params=params)
        return result if isinstance(result, list) else []

    async def get_blueprint(self, blueprint_id: str) -> dict[str, Any]:
        """Get a blueprint's metadata (name, description, version, tags, source)."""
        return await self._request("GET", f"/blueprints/{self._path(blueprint_id)}")

    @staticmethod
    def _config_as_yaml(config: dict[str, Any] | str) -> str:
        """Render a range config as the YAML string the blueprint API expects.

        The API takes `config` as YAML text, not a JSON object -- posting a dict
        fails with "cannot unmarshal object into Go struct field ... of type
        string". Callers naturally pass a dict, so convert here.
        """
        if isinstance(config, str):
            return config
        return yaml.safe_dump(config, default_flow_style=False, sort_keys=False)

    async def create_blueprint(
        self,
        blueprint_id: str,
        config: dict[str, Any] | str | None = None,
        name: str | None = None,
        description: str | None = None,
        version: str | None = None,
        tags: list[str] | None = None,
        min_ludus_version: str | None = None,
    ) -> dict[str, Any]:
        """Create a new blueprint from a range configuration.

        Args:
            blueprint_id: Unique identifier for the blueprint.
            config: The range configuration the blueprint deploys, as a dict or
                YAML string. Dicts are converted to YAML for the API.
            name: Human-readable name (defaults to blueprint_id server-side).
            description: What the blueprint builds.
            version: Blueprint version string, e.g. "1.0.0".
            tags: Tags used for discovery and filtering.
            min_ludus_version: Minimum Ludus version required to deploy it.
        """
        payload: dict[str, Any] = {"blueprintID": blueprint_id}
        for key, value in (
            ("name", name),
            ("description", description),
            ("version", version),
            ("tags", tags),
            ("min_ludus_version", min_ludus_version),
        ):
            if value is not None:
                payload[key] = value
        if config is not None:
            payload["config"] = self._config_as_yaml(config)
        return await self._request("POST", "/blueprints", json_data=payload)

    async def export_blueprint(self, blueprint_id: str, output_path: str) -> dict[str, Any]:
        """Export a blueprint to a .tar.gz archive on disk.

        The endpoint serves gzip, not JSON, so the body is written out verbatim.
        """
        result = await self._request(
            "GET", f"/blueprints/{self._path(blueprint_id)}/export", raw=True
        )
        content = result.get("content", b"") if isinstance(result, dict) else b""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return {
            "blueprintID": blueprint_id,
            "path": str(path),
            "size_bytes": len(content),
        }

    async def import_blueprint(self, archive_path: str) -> dict[str, Any]:
        """Import a blueprint from a .tar.gz archive produced by export_blueprint."""
        path = Path(archive_path)
        if not path.is_file():
            raise ValueError(f"Archive not found: {archive_path}")
        files = {"archive": (path.name, path.read_bytes(), "application/gzip")}
        return await self._request("POST", "/blueprints/import", files=files)

    async def install_blueprint(
        self,
        blueprint_id: str,
        make_global: bool = False,
        force_roles: bool = False,
    ) -> dict[str, Any]:
        """Install a blueprint's dependencies (Ansible roles and collections).

        Run this before deploying a blueprint that came from a source, otherwise
        the deployment fails on missing roles.

        Args:
            make_global: Install roles globally rather than for the calling user.
            force_roles: Reinstall roles that are already present.
        """
        payload = {"global": make_global, "forceRoles": force_roles}
        return await self._request(
            "POST", f"/blueprints/{self._path(blueprint_id)}/install", json_data=payload
        )

    async def create_blueprint_from_range(self, range_id: str, blueprint_id: str | None = None) -> dict[str, Any]:
        """Create a blueprint from an existing range.

        Args:
            range_id: ID of the range to create blueprint from
            blueprint_id: ID for the new blueprint. If not provided, uses range_id.
        """
        payload: dict[str, Any] = {"rangeID": range_id, "blueprintID": blueprint_id or range_id}
        return await self._request("POST", "/blueprints/from-range", json_data=payload)

    async def apply_blueprint(
        self, blueprint_id: str, range_id: str, force: bool = False
    ) -> dict[str, Any]:
        """Apply a blueprint to a range, replacing that range's configuration.

        Args:
            force: Apply even if the range is currently deploying.
        """
        payload: dict[str, Any] = {"rangeID": range_id}
        if force:
            payload["force"] = True
        return await self._request(
            "POST", f"/blueprints/{self._path(blueprint_id)}/apply", json_data=payload
        )

    async def copy_blueprint(
        self,
        blueprint_id: str,
        new_blueprint_id: str | None = None,
        name: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Copy a blueprint under a new ID.

        Args:
            new_blueprint_id: ID for the copy. Server generates one if omitted.
            name: Name for the copy.
            description: Description for the copy.
        """
        payload: dict[str, Any] = {}
        for key, value in (
            ("blueprintID", new_blueprint_id),
            ("name", name),
            ("description", description),
        ):
            if value is not None:
                payload[key] = value
        return await self._request(
            "POST",
            f"/blueprints/{self._path(blueprint_id)}/copy",
            json_data=payload or None,
        )

    async def delete_blueprint(self, blueprint_id: str) -> dict[str, Any]:
        """Delete a blueprint."""
        return await self._request("DELETE", f"/blueprints/{self._path(blueprint_id)}")

    async def get_blueprint_config(self, blueprint_id: str) -> dict[str, Any]:
        """Get blueprint configuration."""
        return await self._request("GET", f"/blueprints/{self._path(blueprint_id)}/config")

    async def update_blueprint_config(
        self, blueprint_id: str, config: dict[str, Any] | str
    ) -> dict[str, Any]:
        """Update a blueprint's range configuration.

        The API expects {"config": "<yaml text>"}, not the config object itself.
        """
        return await self._request(
            "PUT",
            f"/blueprints/{self._path(blueprint_id)}/config",
            json_data={"config": self._config_as_yaml(config)},
        )

    async def share_blueprint_with_users(self, blueprint_id: str, user_ids: list[str]) -> dict[str, Any]:
        """Share a blueprint with users."""
        return await self._request("POST", f"/blueprints/{self._path(blueprint_id)}/share/users", json_data={"userIDs": user_ids})

    async def unshare_blueprint_with_users(self, blueprint_id: str, user_ids: list[str]) -> dict[str, Any]:
        """Unshare a blueprint from users."""
        return await self._request("DELETE", f"/blueprints/{self._path(blueprint_id)}/share/users", json_data={"userIDs": user_ids})

    async def share_blueprint_with_groups(self, blueprint_id: str, group_names: list[str]) -> dict[str, Any]:
        """Share a blueprint with groups."""
        return await self._request("POST", f"/blueprints/{self._path(blueprint_id)}/share/groups", json_data={"groupNames": group_names})

    async def unshare_blueprint_with_groups(self, blueprint_id: str, group_names: list[str]) -> dict[str, Any]:
        """Unshare a blueprint from groups."""
        return await self._request("DELETE", f"/blueprints/{self._path(blueprint_id)}/share/groups", json_data={"groupNames": group_names})

    async def list_blueprint_access_users(self, blueprint_id: str) -> list[dict[str, Any]]:
        """List users with access to a blueprint."""
        result = await self._request("GET", f"/blueprints/{self._path(blueprint_id)}/access/users")
        return result if isinstance(result, list) else []

    async def list_blueprint_access_groups(self, blueprint_id: str) -> list[dict[str, Any]]:
        """List groups with access to a blueprint."""
        result = await self._request("GET", f"/blueprints/{self._path(blueprint_id)}/access/groups")
        return result if isinstance(result, list) else []

    # Group Management (v2 only)
    async def list_groups(self) -> list[dict[str, Any]]:
        """List all groups."""
        result = await self._request("GET", "/groups")
        return result if isinstance(result, list) else []

    async def create_group(self, name: str) -> dict[str, Any]:
        """Create a new group."""
        return await self._request("POST", "/groups", json_data={"name": name})

    async def delete_group(self, group_name: str) -> dict[str, Any]:
        """Delete a group."""
        return await self._request("DELETE", f"/groups/{self._path(group_name)}")

    async def add_users_to_group(self, group_name: str, user_ids: list[str]) -> dict[str, Any]:
        """Add users to a group."""
        return await self._request("POST", f"/groups/{self._path(group_name)}/users", json_data={"userIDs": user_ids})

    async def remove_users_from_group(self, group_name: str, user_ids: list[str]) -> dict[str, Any]:
        """Remove users from a group."""
        return await self._request("DELETE", f"/groups/{self._path(group_name)}/users", json_data={"userIDs": user_ids})

    async def list_group_members(self, group_name: str) -> list[dict[str, Any]]:
        """List group members."""
        result = await self._request("GET", f"/groups/{self._path(group_name)}/users")
        return result if isinstance(result, list) else []

    async def add_ranges_to_group(self, group_name: str, range_ids: list[str]) -> dict[str, Any]:
        """Add ranges to a group."""
        return await self._request("POST", f"/groups/{self._path(group_name)}/ranges", json_data={"rangeIDs": range_ids})

    async def remove_ranges_from_group(self, group_name: str, range_ids: list[str]) -> dict[str, Any]:
        """Remove ranges from a group."""
        return await self._request("DELETE", f"/groups/{self._path(group_name)}/ranges", json_data={"rangeIDs": range_ids})

    async def list_group_ranges(self, group_name: str) -> list[dict[str, Any]]:
        """List group ranges."""
        result = await self._request("GET", f"/groups/{self._path(group_name)}/ranges")
        return result if isinstance(result, list) else []

    # VM Management (v2 only)
    async def destroy_vm(self, vm_id: str) -> dict[str, Any]:
        """Destroy a specific VM."""
        return await self._request("DELETE", f"/vm/{self._path(vm_id)}")

    async def get_console_ticket(
        self, vm_id: str, user_id: str | None = None
    ) -> dict[str, Any]:
        """Get a console WebSocket ticket for a VM.

        Args:
            vm_id: Proxmox VM ID or VM name (names are resolved to IDs).
            user_id: Owner of the VM, for admins opening someone else's console.

        Note: the query parameter is ``VMID`` and the API is case-sensitive about
        it — sending ``vmID`` returns HTTP 400 "Invalid VMID".
        """
        resolved = str(vm_id)
        if not resolved.isdigit():
            try:
                ids = await self.resolve_vm_ids([resolved], user_id=user_id)
            except ValueError as e:
                raise LudusNotFoundError(str(e)) from e
            if not ids:
                raise LudusNotFoundError(
                    f"No VM named '{vm_id}' found in the range. "
                    "Pass a Proxmox VM ID or a VM name from get_range."
                )
            resolved = str(ids[0])

        params: dict[str, Any] = {"VMID": resolved}
        if user_id:
            params["userID"] = user_id
        return await self._request("GET", "/vm/console/ticket", params=params)

    def build_console_view_url(self, ticket: str) -> dict[str, Any]:
        """Build the console URL for a ticket from get_console_ticket.

        Despite being documented as a plain GET, /vm/console/view is a WebSocket
        upgrade endpoint — the VNC data channel itself. Requesting it over HTTP
        always returns 400 "Failed to upgrade connection to WebSocket", so this
        returns the URL to connect to instead of fetching it.
        """
        base = self.base_url.rstrip("/")
        http_url = f"{base}{self._base_path}/vm/console/view?ticket={quote(ticket, safe='')}"
        ws_url = http_url.replace("https://", "wss://", 1).replace("http://", "ws://", 1)
        return {
            "websocket_url": ws_url,
            "http_url": http_url,
            "protocol": "websocket",
            "note": (
                "This endpoint is a WebSocket VNC channel, not an HTML page. "
                "Connect a VNC/noVNC client to websocket_url; a plain HTTP GET "
                "returns 400 'Failed to upgrade connection to WebSocket'."
            ),
            "ticket_expires": "Console tickets are short-lived; request a new one if it fails.",
        }

    async def get_openapi_spec(self) -> dict[str, Any]:
        """Fetch the server's own OpenAPI specification.

        Useful for discovering endpoints supported by this particular Ludus
        version rather than assuming the ones this client was written against.
        """
        return await self._request("GET", "/openapi", raw=True)

    # Diagnostics (v2 only)
    async def get_diagnostics(self) -> dict[str, Any]:
        """Get system diagnostics."""
        return await self._request("GET", "/diagnostics")

    async def whoami(self) -> dict[str, Any]:
        """Test authentication and get user info."""
        return await self._request("GET", "/whoami")

    async def get_license(self) -> dict[str, Any]:
        """Get license information."""
        return await self._request("GET", "/license")

    # Migration (v2 only)
    async def migrate_sqlite_to_pocketbase(self) -> dict[str, Any]:
        """Migrate from SQLite to PocketBase."""
        return await self._request("POST", "/migrate/sqlite")

    async def get_sdn_migration_status(self) -> dict[str, Any]:
        """Get SDN migration status."""
        return await self._request("GET", "/migrate/sdn/status")

    async def migrate_to_sdn(self) -> dict[str, Any]:
        """Migrate to SDN networking."""
        return await self._request("POST", "/migrate/sdn")

    async def setup_sdn(self) -> dict[str, Any]:
        """Setup SDN infrastructure."""
        return await self._request("POST", "/sdn/setup")

    # Enhanced Range Management (v2 only)
    async def create_range(self, name: str, range_id: str | None = None, description: str | None = None) -> dict[str, Any]:
        """Create a new range.

        Args:
            name: Display name for the range
            range_id: Range ID (alphanumeric identifier). If not provided, derived from name.
            description: Optional range description
        """
        payload: dict[str, Any] = {"name": name}
        if range_id:
            payload["rangeID"] = range_id
        if description:
            payload["description"] = description
        return await self._request("POST", "/ranges/create", json_data=payload)

    async def assign_range_to_user(self, user_id: str, range_id: str) -> dict[str, Any]:
        """Assign range access to a user."""
        return await self._request("POST", f"/ranges/assign/{self._path(user_id)}/{self._path(range_id)}")

    async def revoke_range_from_user(self, user_id: str, range_id: str) -> dict[str, Any]:
        """Revoke range access from a user."""
        return await self._request("DELETE", f"/ranges/revoke/{self._path(user_id)}/{self._path(range_id)}")

    async def list_range_users(self, range_id: str) -> list[dict[str, Any]]:
        """List users with access to a range."""
        result = await self._request("GET", f"/ranges/{self._path(range_id)}/users")
        return result if isinstance(result, list) else []

    async def list_accessible_ranges(self) -> list[dict[str, Any]]:
        """List ranges accessible to current user."""
        result = await self._request("GET", "/ranges/accessible")
        return result if isinstance(result, list) else []

    async def get_default_range(self) -> dict[str, Any]:
        """Get user's default range ID."""
        return await self._request("GET", "/user/default-range")

    async def set_default_range(self, range_id: str) -> dict[str, Any]:
        """Set user's default range."""
        return await self._request("POST", "/user/default-range", json_data={"rangeID": range_id})

    async def get_user_memberships(self) -> list[dict[str, Any]]:
        """Get current user's group memberships."""
        result = await self._request("GET", "/user/memberships")
        return result if isinstance(result, list) else []

    # Enhanced Ansible (v2 only)
    async def move_role_scope(
        self,
        role_name: str | list[str],
        scope: str | bool = "global",
        copy: bool = False,
    ) -> dict[str, Any]:
        """Move Ansible roles between user and global scope.

        The API takes {"roles": [...], "global": bool}; a {"name", "scope"} body
        is rejected with "At least one role name is required".

        Args:
            role_name: Role name, or a list of role names.
            scope: "global" or "user" (booleans are accepted too, where True
                means global).
            copy: Copy the role into the target scope instead of moving it.
        """
        roles = [role_name] if isinstance(role_name, str) else list(role_name)
        if not roles:
            raise ValueError("At least one role name is required")

        if isinstance(scope, bool):
            make_global = scope
        else:
            normalized = str(scope).strip().lower()
            if normalized not in ("global", "user"):
                raise ValueError(
                    f"Unknown scope '{scope}'. Use 'global' or 'user'."
                )
            make_global = normalized == "global"

        payload: dict[str, Any] = {"roles": roles, "global": make_global}
        if copy:
            payload["copy"] = True
        return await self._request("PATCH", "/ansible/role/scope", json_data=payload)

    async def get_role_vars(self, role_name: str | list[str]) -> dict[str, Any]:
        """Get Ansible role variables.

        The API takes a "roles" ARRAY; sending {"name": ...} was rejected with
        "At least one role name is required".
        """
        roles = [role_name] if isinstance(role_name, str) else list(role_name)
        if not roles:
            raise ValueError("get_role_vars() requires at least one role name.")
        return await self._request("POST", "/ansible/role/vars", json_data={"roles": roles})

    async def list_subscription_roles(self) -> list[dict[str, Any]]:
        """List subscription roles (enterprise)."""
        result = await self._request("GET", "/ansible/subscription-roles")
        return result if isinstance(result, list) else []

    async def install_subscription_roles(self, roles: list[str]) -> dict[str, Any]:
        """Install subscription roles (enterprise)."""
        return await self._request("POST", "/ansible/subscription-roles", json_data={"roles": roles})

    # Enhanced User (v2 only)
    async def provision_oauth2_user(self, config: dict[str, Any]) -> dict[str, Any]:
        """Provision an OAuth2 user."""
        return await self._request("POST", "/user/provision-oauth2", json_data=config)

    async def reset_user_proxmox_password(self, user_id: str) -> dict[str, Any]:
        """Reset a user's Proxmox password (admin only)."""
        return await self._request(
            "POST", "/user/credentials", json_data={"userID": user_id}
        )

    async def get_user_proxmox_credentials(self, user_id: str | None = None) -> dict[str, Any]:
        """Get Proxmox credentials for a user.
        
        Args:
            user_id: Optional user ID (defaults to caller's user if not specified)
        """
        params = {}
        if user_id:
            params["userID"] = user_id
        return await self._request("GET", "/user/credentials", params=params)

    async def set_user_proxmox_credentials(
        self,
        proxmox_password: str,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Set the Proxmox password for a user.
        
        Args:
            proxmox_password: New Proxmox password
            user_id: Optional user ID (defaults to caller's user if not specified)
                    Admins can set other users' passwords
        """
        payload = {"proxmoxPassword": proxmox_password}
        if user_id:
            payload["userID"] = user_id
        return await self._request("POST", "/user/credentials", json_data=payload)

    # ==================== QUOTAS (v2) ====================
    # Quotas cap what a user or group may consume: RAM (MB), CPU cores,
    # VM count and concurrent ranges.

    async def get_user_quotas(self, user_id: str | None = None) -> dict[str, Any]:
        """Get quotas for a user (defaults to the caller)."""
        params = {}
        if user_id:
            params["userID"] = user_id
        return await self._request("GET", "/user/quotas", params=params)

    async def get_all_user_quotas(self) -> list[dict[str, Any]]:
        """Get quotas for every user (admin only)."""
        result = await self._request("GET", "/user/quotas/all")
        return result if isinstance(result, list) else []

    async def get_default_quotas(self) -> dict[str, Any]:
        """Get the server-wide default quotas applied to new users."""
        return await self._request("GET", "/user/quotas/defaults")

    async def set_user_quotas(
        self,
        user_ids: list[str],
        quota_ram: int | None = None,
        quota_cpu: int | None = None,
        quota_vms: int | None = None,
        quota_ranges: int | None = None,
    ) -> dict[str, Any]:
        """Set quotas for one or more users (admin only).

        Only the quotas you pass are changed; omitted ones keep their current value.

        Args:
            user_ids: Users to apply the quotas to.
            quota_ram: RAM limit in MB.
            quota_cpu: CPU core limit.
            quota_vms: Maximum number of VMs.
            quota_ranges: Maximum number of concurrent ranges.
        """
        if not user_ids:
            raise ValueError("user_ids must contain at least one user ID")

        payload: dict[str, Any] = {"userIDs": user_ids}
        for key, value in (
            ("quotaRAM", quota_ram),
            ("quotaCPU", quota_cpu),
            ("quotaVMs", quota_vms),
            ("quotaRanges", quota_ranges),
        ):
            if value is not None:
                payload[key] = value
        return await self._request("PUT", "/user/quotas", json_data=payload)

    async def get_group_quotas(self) -> list[dict[str, Any]]:
        """Get the default quotas configured for each group (admin only)."""
        result = await self._request("GET", "/groups/quotas")
        return result if isinstance(result, list) else []

    async def set_group_quotas(
        self,
        group_names: list[str],
        default_quota_ram: int | None = None,
        default_quota_cpu: int | None = None,
        default_quota_vms: int | None = None,
        default_quota_ranges: int | None = None,
    ) -> dict[str, Any]:
        """Set default quotas for one or more groups (admin only).

        These apply to members of the group who have no explicit user quota.
        """
        if not group_names:
            raise ValueError("group_names must contain at least one group name")

        payload: dict[str, Any] = {"groupNames": group_names}
        for key, value in (
            ("defaultQuotaRAM", default_quota_ram),
            ("defaultQuotaCPU", default_quota_cpu),
            ("defaultQuotaVMs", default_quota_vms),
            ("defaultQuotaRanges", default_quota_ranges),
        ):
            if value is not None:
                payload[key] = value
        return await self._request("PUT", "/groups/quotas", json_data=payload)

    # ==================== AUTO-SHUTDOWN (v2) ====================

    async def get_auto_shutdown(
        self, range_id: str | None = None, user_id: str | None = None
    ) -> dict[str, Any]:
        """Get the auto-shutdown timeout for a range."""
        params = {}
        if range_id:
            params["rangeID"] = range_id
        if user_id:
            params["userID"] = user_id
        return await self._request("GET", "/range/auto-shutdown", params=params)

    async def set_auto_shutdown(
        self,
        timeout_minutes: int,
        range_id: str | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Set the auto-shutdown timeout for a range.

        Args:
            timeout_minutes: Idle minutes before the range powers off. 0 disables it.
        """
        if timeout_minutes < 0:
            raise ValueError("timeout_minutes must be 0 (disabled) or a positive number of minutes")

        params = {}
        if range_id:
            params["rangeID"] = range_id
        if user_id:
            params["userID"] = user_id
        return await self._request(
            "PUT",
            "/range/auto-shutdown",
            json_data={"autoShutdownTimeout": timeout_minutes},
            params=params,
        )

    # ==================== DEPLOYMENT LOG HISTORY (v2) ====================
    # Ludus keeps prior deployment/build logs, not just the currently running one.

    async def list_range_log_history(
        self, range_id: str | None = None, user_id: str | None = None
    ) -> list[dict[str, Any]]:
        """List past range deployment logs (most recent first)."""
        params = {}
        if range_id:
            params["rangeID"] = range_id
        if user_id:
            params["userID"] = user_id
        result = await self._request("GET", "/range/logs/history", params=params)
        return result if isinstance(result, list) else []

    async def get_range_log_from_history(
        self, log_id: str, range_id: str | None = None
    ) -> dict[str, Any]:
        """Get the contents of one archived range deployment log."""
        params = {}
        if range_id:
            params["rangeID"] = range_id
        return await self._request(
            "GET", f"/range/logs/history/{self._path(log_id)}", params=params
        )

    async def list_template_log_history(self) -> list[dict[str, Any]]:
        """List past template build logs (most recent first)."""
        result = await self._request("GET", "/templates/logs/history")
        return result if isinstance(result, list) else []

    async def get_template_log_from_history(self, log_id: str) -> dict[str, Any]:
        """Get the contents of one archived template build log."""
        return await self._request("GET", f"/templates/logs/history/{self._path(log_id)}")

    # ==================== SOURCES (v2 content catalogs) ====================
    # A "source" is a git repo or uploaded archive that publishes blueprints,
    # packer templates, Ansible roles and collections for installation.

    async def list_sources(self) -> list[dict[str, Any]]:
        """List configured content sources (v2 only)."""
        result = await self._request("GET", "/sources")
        return result if isinstance(result, list) else []

    async def get_source(self, source_id: str) -> dict[str, Any]:
        """Get details for a single source (v2 only)."""
        return await self._request("GET", f"/sources/{self._path(source_id)}")

    async def get_source_catalog(self, source_id: str) -> dict[str, Any]:
        """Get the full catalog (blueprints, templates, roles, collections)."""
        return await self._request("GET", f"/sources/{self._path(source_id)}/catalog")

    async def list_source_templates(self, source_id: str) -> list[dict[str, Any]]:
        """List packer templates published by a source."""
        result = await self._request("GET", f"/sources/{self._path(source_id)}/templates")
        return result if isinstance(result, list) else []

    async def list_source_blueprints(self, source_id: str) -> list[dict[str, Any]]:
        """List blueprints published by a source."""
        result = await self._request("GET", f"/sources/{self._path(source_id)}/blueprints")
        return result if isinstance(result, list) else []

    async def list_source_roles(self, source_id: str) -> list[dict[str, Any]]:
        """List Ansible roles published by a source."""
        result = await self._request("GET", f"/sources/{self._path(source_id)}/roles")
        return result if isinstance(result, list) else []

    async def list_source_collections(self, source_id: str) -> list[dict[str, Any]]:
        """List Ansible collections published by a source."""
        result = await self._request("GET", f"/sources/{self._path(source_id)}/collections")
        return result if isinstance(result, list) else []

    async def install_from_source(
        self,
        source_id: str,
        templates: list[str] | None = None,
        blueprints: list[str] | None = None,
        roles: list[str] | None = None,
        collections: list[str] | None = None,
        install_globally: bool = False,
        force: bool = False,
        no_deps: bool = False,
    ) -> dict[str, Any]:
        """Install selected items from a source.

        The selection REPLACES the source's persisted selection - items added
        upstream later do not extend it, and omitting a category leaves it
        empty. Pass everything you want installed in one call.

        Args:
            source_id: Source to install from
            templates: Packer template names
            blueprints: sourceBlueprintID values
            roles: Source-bundled role names
            collections: Source-bundled collection FQCNs (namespace.name)
            install_globally: Admin only - install roles/collections for all users
            force: Reinstall items that are already present
            no_deps: Skip installing dependencies of the selected items
        """
        selection: dict[str, list[str]] = {}
        if templates:
            selection["templates"] = list(templates)
        if blueprints:
            selection["blueprints"] = list(blueprints)
        if roles:
            selection["localRoles"] = list(roles)
        if collections:
            selection["localCollections"] = list(collections)

        if not selection:
            raise ValueError(
                "install_from_source() needs at least one of templates, "
                "blueprints, roles or collections."
            )

        payload: dict[str, Any] = {"selection": selection}
        if install_globally:
            payload["global"] = True
        if force:
            payload["force"] = True
        if no_deps:
            payload["noDeps"] = True

        return await self._request("POST", f"/sources/{self._path(source_id)}/install", json_data=payload)

    async def sync_source(self, source_id: str) -> dict[str, Any]:
        """Re-fetch a source so its catalog reflects upstream."""
        return await self._request("POST", f"/sources/{self._path(source_id)}/sync")

    async def delete_source(self, source_id: str) -> dict[str, Any]:
        """Remove a source (does not uninstall what it already installed)."""
        return await self._request("DELETE", f"/sources/{self._path(source_id)}")

    async def add_source(
        self,
        source_id: str,
        source_type: str = "git",
        url: str | None = None,
        ref: str | None = None,
        archive_path: str | None = None,
        make_global: bool = False,
        force: bool = False,
    ) -> dict[str, Any]:
        """Register a new content source.

        Args:
            source_id: Identifier to give the source (e.g. "ludus-source-bsl").
            source_type: "git" for a repository, "archive" for an uploaded tarball.
            url: Git URL. Required when source_type is "git".
            ref: Branch, tag or commit to track. Defaults to the repo's default branch.
            archive_path: Local path to a .tar.gz. Required when source_type is "archive".
            make_global: Make the source available to all users (admin only).
            force: Overwrite an existing source with the same ID.
        """
        if source_type == "git" and not url:
            raise ValueError("url is required when source_type is 'git'")
        if source_type == "archive" and not archive_path:
            raise ValueError("archive_path is required when source_type is 'archive'")

        form: dict[str, Any] = {
            "id": source_id,
            "type": source_type,
            "global": str(make_global).lower(),
            "force": str(force).lower(),
        }
        if url:
            form["url"] = url
        if ref:
            form["ref"] = ref

        files = None
        if archive_path:
            path = Path(archive_path)
            if not path.is_file():
                raise ValueError(f"Archive not found: {archive_path}")
            files = {"archive": (path.name, path.read_bytes(), "application/gzip")}

        return await self._request("POST", "/sources", data=form, files=files)

    async def update_source(
        self,
        source_id: str,
        url: str | None = None,
        ref: str | None = None,
        archive_path: str | None = None,
        make_global: bool | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """Update an existing source's URL, tracked ref, or backing archive.

        Only the fields you pass are changed.
        """
        form: dict[str, Any] = {"force": str(force).lower()}
        if url:
            form["url"] = url
        if ref:
            form["ref"] = ref
        if make_global is not None:
            form["global"] = str(make_global).lower()

        files = None
        if archive_path:
            path = Path(archive_path)
            if not path.is_file():
                raise ValueError(f"Archive not found: {archive_path}")
            files = {"archive": (path.name, path.read_bytes(), "application/gzip")}

        return await self._request(
            "PATCH", f"/sources/{self._path(source_id)}", data=form, files=files
        )

    async def regenerate_user_apikey(self, user_id: str | None = None) -> dict[str, Any]:
        """Issue a NEW API key for a user, invalidating the old one (admin only).

        Despite being a GET, this endpoint is destructive: it mints a fresh key
        every time it is called and there is no way to read back an existing
        key. Callers must not treat it as a lookup.

        Args:
            user_id: Optional user ID (defaults to caller's user if not specified)
        """
        params = {}
        if user_id:
            params["userID"] = user_id
        return await self._request("GET", "/user/apikey", params=params)

    async def get_user_wireguard(self, user_id: str | None = None) -> str:
        """Get user WireGuard configuration.
        
        Args:
            user_id: Optional user ID (defaults to caller's user if not specified)
        """
        params = {}
        if user_id:
            params["userID"] = user_id
        result = await self._request("GET", "/user/wireguard", params=params)
        return result.get("result", {}).get("wireGuardConfig", "") if isinstance(result, dict) else str(result)

    async def update_user_proxmox_creds(
        self,
        user_id: str,
        proxmox_username: str,
        proxmox_password: str,
    ) -> dict[str, Any]:
        """Update user's Proxmox credentials (admin only).
        
        Note: This is a convenience method that calls set_user_proxmox_credentials.
        The API only supports setting the password, not the username.
        """
        return await self.set_user_proxmox_credentials(proxmox_password, user_id)

