"""Three-legged OAuth 1.0 account connection for FatSecret."""

from __future__ import annotations

import hmac
import os
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from smart_basket.fatsecret.client import AUTHORIZE_URL, FatSecretClient


class FatSecretOAuthError(RuntimeError):
    """The FatSecret authorization flow could not be completed safely."""


@dataclass(frozen=True)
class FatSecretSettings:
    consumer_key: str
    consumer_secret: str
    callback_url: str
    frontend_url: str
    timeout: float = 10.0

    @classmethod
    def from_env(cls) -> "FatSecretSettings":
        consumer_key = os.getenv("FATSECRET_CONSUMER_KEY", "").strip()
        consumer_secret = os.getenv("FATSECRET_CONSUMER_SECRET", "").strip()
        if not consumer_key or not consumer_secret:
            raise FatSecretOAuthError("FatSecret developer credentials are not configured.")
        try:
            timeout = float(os.getenv("FATSECRET_TIMEOUT_SECONDS", "10"))
        except ValueError as exc:
            raise FatSecretOAuthError("FATSECRET_TIMEOUT_SECONDS must be numeric.") from exc
        if timeout <= 0:
            raise FatSecretOAuthError("FATSECRET_TIMEOUT_SECONDS must be positive.")
        return cls(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            callback_url=os.getenv(
                "FATSECRET_OAUTH_CALLBACK_URL",
                "http://localhost:8000/api/auth/fatsecret/callback",
            ),
            frontend_url=os.getenv("SMART_BASKET_FRONTEND_URL", "http://localhost:3000"),
            timeout=timeout,
        )


class FatSecretOAuthManager:
    def __init__(self, *, settings_factory=None, client_factory=None):
        self._settings_factory = settings_factory or FatSecretSettings.from_env
        self._client_factory = client_factory or FatSecretClient

    def _client(self, settings: FatSecretSettings) -> FatSecretClient:
        return self._client_factory(
            settings.consumer_key,
            settings.consumer_secret,
            timeout=settings.timeout,
        )

    async def start(self, owner) -> str:
        settings = self._settings_factory()
        credentials = await self._client(settings).request_token(settings.callback_url)
        with owner.lock:
            owner.fatsecret_request_token = credentials.token
            owner.fatsecret_request_secret = credentials.secret
        return f"{AUTHORIZE_URL}?{urlencode({'oauth_token': credentials.token})}"

    async def finish(self, owner, *, oauth_token: str, oauth_verifier: str) -> None:
        settings = self._settings_factory()
        with owner.lock:
            expected_token = owner.fatsecret_request_token
            request_secret = owner.fatsecret_request_secret
        if not expected_token or not request_secret:
            raise FatSecretOAuthError("No FatSecret authorization is pending in this session.")
        if not hmac.compare_digest(expected_token, oauth_token):
            raise FatSecretOAuthError("FatSecret returned a token for another authorization flow.")
        try:
            credentials = await self._client(settings).access_token(
                oauth_token,
                request_secret,
                oauth_verifier,
            )
        except Exception:
            await self.cancel(owner)
            raise
        with owner.lock:
            owner.fatsecret_access_token = credentials.token
            owner.fatsecret_access_secret = credentials.secret
            owner.fatsecret_connected = True
            owner.fatsecret_account_label = "Connected FatSecret account"
            owner.fatsecret_request_token = None
            owner.fatsecret_request_secret = None

    async def cancel(self, owner) -> None:
        with owner.lock:
            owner.fatsecret_request_token = None
            owner.fatsecret_request_secret = None

    async def delegated_call(
        self,
        owner,
        api_method: str,
        parameters: Mapping[str, object] | None = None,
    ) -> dict[str, Any]:
        """Call FatSecret without exposing a session's token pair to consumers."""

        settings = self._settings_factory()
        with owner.lock:
            connected = owner.fatsecret_connected
            access_token = owner.fatsecret_access_token
            access_secret = owner.fatsecret_access_secret
        if not connected or not access_token or not access_secret:
            raise FatSecretOAuthError("Connect a FatSecret account before using profile APIs.")
        return await self._client(settings).call(
            api_method,
            parameters,
            access_token=access_token,
            access_secret=access_secret,
        )

    def return_url(self, *, connected: bool) -> str:
        try:
            target = self._settings_factory().frontend_url
        except FatSecretOAuthError:
            target = os.getenv("SMART_BASKET_FRONTEND_URL", "http://localhost:3000")
        parts = urlsplit(target)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query["fatsecret"] = "connected" if connected else "error"
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
