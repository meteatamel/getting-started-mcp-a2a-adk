from urllib.parse import urlparse

from google.adk.tools.mcp_tool.mcp_session_manager import (
    IS_MCP_SDK_V2,
    create_mcp_http_client,
)
from google.auth.transport.requests import Request
from google.oauth2 import id_token

if IS_MCP_SDK_V2:
    import httpx2 as httpx
else:
    import httpx


class GoogleIdTokenAuth(httpx.Auth):
    """Attaches a Google-signed OIDC ID token to outgoing Cloud Run HTTP requests."""

    def __init__(self, target_url: str):
        parsed = urlparse(target_url)
        # Cloud Run OIDC audience must be the root service origin (without /mcp)
        self.audience = f"{parsed.scheme}://{parsed.netloc}"
        self._creds = None

    def auth_flow(self, request: httpx.Request):
        if self._creds is None:
            self._creds = id_token.fetch_id_token_credentials(self.audience)
        if not self._creds.valid:
            self._creds.refresh(Request())
        request.headers["Authorization"] = f"Bearer {self._creds.token}"
        yield request


def get_mcp_http_client_factory(mcp_server_url: str):
    """Returns an MCP HTTP client factory that injects OIDC ID tokens for HTTPS Cloud Run URLs."""
    if not mcp_server_url.startswith("https://"):
        return create_mcp_http_client

    auth = GoogleIdTokenAuth(mcp_server_url)

    def factory(
        headers: dict[str, str] | None = None,
        timeout: httpx.Timeout | None = None,
        **_kwargs,
    ) -> httpx.AsyncClient:
        return create_mcp_http_client(headers=headers, timeout=timeout, auth=auth)

    return factory
