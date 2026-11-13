from urllib.parse import urlparse

from google.auth.transport.requests import Request
from google.oauth2 import id_token
import httpx


class GoogleIdTokenAuth(httpx.Auth):
    """Attaches a Google-signed OIDC ID token to outgoing Cloud Run HTTP requests."""

    def __init__(self, target_url: str):
        parsed = urlparse(target_url)
        self.audience = f"{parsed.scheme}://{parsed.netloc}"
        self._creds = None

    def auth_flow(self, request: httpx.Request):
        if self._creds is None:
            self._creds = id_token.fetch_id_token_credentials(self.audience)
        if not self._creds.valid:
            self._creds.refresh(Request())
        request.headers["Authorization"] = f"Bearer {self._creds.token}"
        yield request


def get_a2a_http_client(
    agent_url: str, timeout: float = 600.0
) -> httpx.AsyncClient | None:
    """Returns an authenticated httpx.AsyncClient for HTTPS Cloud Run A2A agents."""
    if not agent_url.startswith("https://"):
        return None
    return httpx.AsyncClient(
        auth=GoogleIdTokenAuth(agent_url),
        timeout=httpx.Timeout(timeout=timeout),
    )
