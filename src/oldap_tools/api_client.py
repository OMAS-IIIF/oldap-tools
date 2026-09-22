"""Authenticated HTTP transport for OLDAP command-line operations.

One client owns one in-memory cookie/token session. Mutation requests are never
retried after transport failures: their server-side outcome may be unknown.
"""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any
from urllib.parse import quote, urlsplit

import requests


class ApiError(ValueError):
    """An HTTP or protocol failure, retaining status and safe server detail."""

    def __init__(self, message: str, *, status: int | None = None, detail: str = ""):
        super().__init__(message)
        self.status = status
        self.detail = detail


def api_path(*parts: str) -> str:
    """Encode individual path components, including project/QName identifiers."""
    return "/" + "/".join(quote(str(part), safe="") for part in parts)


@dataclass(frozen=True)
class ApiOperation:
    """One planned HTTP mutation; payload is JSON, never credentials.

    ``remove_unused`` marks a class-property removal for which the existing
    server's explicit in-use refusal should preserve the property and continue.
    """

    method: str
    path: str
    payload: dict[str, Any] | None = None
    remove_unused: bool = False


class OldapApiClient:
    """Use existing OLDAP login/refresh endpoints without GraphDB access.

    Args:
        base_url: OLDAP API root, optionally including a deployment path.
        timeout: Per-request connect/read timeout in seconds.

    The caller must close the client (preferably with a context manager). Tokens
    and refresh cookies are neither persisted nor included in diagnostics.
    """

    def __init__(self, base_url: str, *, timeout: float = 60):
        parsed = urlsplit(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ApiError("--api must be an HTTP(S) API URL without credentials, query or fragment.")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self._token: str | None = None
        self._expires_at: float | None = None

    def __enter__(self) -> OldapApiClient:
        return self

    def __exit__(self, *_args) -> None:
        self.session.close()
        self._token = None

    def login(self, user: str, password: str) -> None:
        """Authenticate once; keep the API's refresh cookie in this session."""
        response = self._send("POST", api_path("admin", "auth", user), json={"password": password}, authenticated=False)
        self._set_token(self._json(response))

    def _set_token(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            raise ApiError("OLDAP authentication returned an invalid response.")
        token = payload.get("accessToken") or payload.get("token")
        if not isinstance(token, str) or not token:
            raise ApiError("OLDAP authentication returned no access token.")
        self._token = token
        ttl = payload.get("expiresIn")
        self._expires_at = time.monotonic() + max(0, ttl - 30) if isinstance(ttl, (int, float)) else None

    @staticmethod
    def _json(response: requests.Response) -> Any:
        try:
            return response.json()
        except ValueError as error:
            raise ApiError("OLDAP API returned invalid JSON.") from error

    def _send(self, method: str, path: str, *, authenticated: bool = True, **kwargs) -> requests.Response:
        headers = {"Accept": "application/json"}
        if authenticated:
            if self._token is None:
                raise ApiError("OLDAP API client is not authenticated.")
            if self._expires_at is not None and time.monotonic() >= self._expires_at:
                response = self._send("POST", "/admin/auth/refresh", authenticated=False)
                self._set_token(self._json(response))
            headers["Authorization"] = f"Bearer {self._token}"
        try:
            response = self.session.request(method, self.base_url + path, headers=headers,
                                            timeout=self.timeout, allow_redirects=False, **kwargs)
        except requests.RequestException as error:
            raise ApiError(f"{method} {path}: transport failed; no retry was attempted. "
                           "A write may already have reached the server; inspect its state before rerunning.") from error
        if not 200 <= response.status_code < 300:
            detail = ""
            # Login/refresh failures must never echo server-returned credentials.
            if authenticated:
                try:
                    body = response.json()
                    if isinstance(body, dict) and isinstance(body.get("message"), str):
                        detail = body["message"][:500]
                except ValueError:
                    pass
                if self._token:
                    detail = detail.replace(self._token, "[redacted]")
            raise ApiError(f"{method} {path}: HTTP {response.status_code}" + (f": {detail}" if detail else ""),
                           status=response.status_code, detail=detail)
        return response

    def get_json(self, path: str, *, missing_ok: bool = False, **params) -> Any:
        """Read JSON; only an explicit HTTP 404 may represent a missing object."""
        try:
            return self._json(self._send("GET", path, params=params or None))
        except ApiError as error:
            if missing_ok and error.status == 404:
                return None
            raise

    def get_bytes(self, path: str) -> bytes:
        """Download an authenticated model or taxonomy export."""
        return self._send("GET", path).content

    def apply(self, operation: ApiOperation) -> None:
        """Execute exactly one mutation without automatic request retries."""
        self._send(operation.method, operation.path, json=operation.payload)
