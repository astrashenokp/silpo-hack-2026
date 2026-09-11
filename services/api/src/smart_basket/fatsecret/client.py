"""OAuth 1.0 signed transport for FatSecret Platform profile APIs."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping
from urllib.parse import parse_qs, quote

import httpx2


REQUEST_TOKEN_URL = "https://authentication.fatsecret.com/oauth/request_token"
AUTHORIZE_URL = "https://authentication.fatsecret.com/oauth/authorize"
ACCESS_TOKEN_URL = "https://authentication.fatsecret.com/oauth/access_token"
REST_API_URL = "https://platform.fatsecret.com/rest/server.api"


class FatSecretClientError(RuntimeError):
    """FatSecret rejected a request or returned a malformed response."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        provider_code: int | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.provider_code = provider_code


@dataclass(frozen=True)
class OAuthCredentials:
    token: str
    secret: str


def percent_encode(value: object) -> str:
    """Encode an OAuth 1.0 value using RFC 3986 rules."""

    return quote(str(value), safe="~-._")


def oauth_signature(
    method: str,
    url: str,
    parameters: Mapping[str, object],
    consumer_secret: str,
    token_secret: str = "",
) -> str:
    """Build an HMAC-SHA1 OAuth 1.0 signature."""

    normalized = "&".join(
        f"{percent_encode(key)}={percent_encode(value)}"
        for key, value in sorted(
            parameters.items(),
            key=lambda item: (percent_encode(item[0]), percent_encode(item[1])),
        )
    )
    base_string = "&".join(
        (method.upper(), percent_encode(url), percent_encode(normalized))
    )
    signing_key = f"{percent_encode(consumer_secret)}&{percent_encode(token_secret)}"
    digest = hmac.new(
        signing_key.encode("utf-8"),
        base_string.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    return base64.b64encode(digest).decode("ascii")


class FatSecretClient:
    """Make application or delegated-user calls to the FatSecret REST API.

    User tokens are supplied per call instead of being retained globally, which
    prevents one application's singleton client from crossing user sessions.
    """

    def __init__(
        self,
        consumer_key: str,
        consumer_secret: str,
        *,
        timeout: float = 10.0,
        nonce_factory: Callable[[], str] | None = None,
        clock: Callable[[], float] | None = None,
        http_client_factory: Callable[..., Any] | None = None,
    ):
        if not consumer_key or not consumer_secret:
            raise ValueError("FatSecret consumer credentials are required.")
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.timeout = timeout
        self._nonce_factory = nonce_factory or (lambda: secrets.token_hex(16))
        self._clock = clock or time.time
        self._http_client_factory = http_client_factory or httpx2.AsyncClient

    def _oauth_parameters(
        self,
        *,
        token: str | None = None,
        callback: str | None = None,
        verifier: str | None = None,
    ) -> dict[str, str]:
        parameters = {
            "oauth_consumer_key": self.consumer_key,
            "oauth_nonce": self._nonce_factory(),
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(self._clock())),
            "oauth_version": "1.0",
        }
        if token is not None:
            parameters["oauth_token"] = token
        if callback is not None:
            parameters["oauth_callback"] = callback
        if verifier is not None:
            parameters["oauth_verifier"] = verifier
        return parameters

    async def _request(
        self,
        method: str,
        url: str,
        *,
        request_parameters: Mapping[str, object] | None = None,
        token: str | None = None,
        token_secret: str = "",
        callback: str | None = None,
        verifier: str | None = None,
    ):
        request_parameters = dict(request_parameters or {})
        oauth_parameters = self._oauth_parameters(
            token=token,
            callback=callback,
            verifier=verifier,
        )
        signing_parameters = {**request_parameters, **oauth_parameters}
        oauth_parameters["oauth_signature"] = oauth_signature(
            method,
            url,
            signing_parameters,
            self.consumer_secret,
            token_secret,
        )
        wire_parameters = {**request_parameters, **oauth_parameters}
        kwargs: dict[str, object] = {}
        if method.upper() == "GET":
            kwargs["params"] = wire_parameters
        else:
            kwargs["data"] = wire_parameters
        async with self._http_client_factory(timeout=self.timeout) as client:
            response = await client.request(method.upper(), url, **kwargs)
        try:
            response.raise_for_status()
        except Exception as exc:
            status_code = getattr(response, "status_code", None)
            raise FatSecretClientError(
                f"FatSecret returned HTTP {status_code or 'error'}.",
                status_code=status_code,
            ) from exc
        return response

    async def request_token(self, callback_url: str) -> OAuthCredentials:
        response = await self._request(
            "POST",
            REQUEST_TOKEN_URL,
            callback=callback_url,
        )
        payload = parse_qs(response.text, keep_blank_values=True)
        token = _single(payload, "oauth_token")
        secret = _single(payload, "oauth_token_secret")
        if payload.get("oauth_callback_confirmed", [""])[0].casefold() != "true":
            raise FatSecretClientError("FatSecret did not confirm the OAuth callback.")
        return OAuthCredentials(token=token, secret=secret)

    async def access_token(
        self,
        request_token: str,
        request_secret: str,
        verifier: str,
    ) -> OAuthCredentials:
        response = await self._request(
            "GET",
            ACCESS_TOKEN_URL,
            token=request_token,
            token_secret=request_secret,
            verifier=verifier,
        )
        payload = parse_qs(response.text, keep_blank_values=True)
        return OAuthCredentials(
            token=_single(payload, "oauth_token"),
            secret=_single(payload, "oauth_token_secret"),
        )

    async def call(
        self,
        api_method: str,
        parameters: Mapping[str, object] | None = None,
        *,
        access_token: str,
        access_secret: str,
    ) -> dict[str, Any]:
        """Call a delegated FatSecret method on behalf of one connected user."""

        payload = {"method": api_method, "format": "json", **dict(parameters or {})}
        response = await self._request(
            "POST",
            REST_API_URL,
            request_parameters=payload,
            token=access_token,
            token_secret=access_secret,
        )
        try:
            data = response.json()
        except Exception as exc:
            raise FatSecretClientError("FatSecret returned invalid JSON.") from exc
        if not isinstance(data, dict):
            raise FatSecretClientError("FatSecret returned an unexpected response.")
        if "error" in data:
            error = data["error"]
            message = error.get("message") if isinstance(error, dict) else None
            raw_code = error.get("code") if isinstance(error, dict) else None
            try:
                provider_code = int(raw_code)
            except (TypeError, ValueError):
                provider_code = None
            raise FatSecretClientError(
                message or "FatSecret rejected the API request.",
                provider_code=provider_code,
            )
        return data

    async def search_food(
        self,
        query: str,
        *,
        access_token: str,
        access_secret: str,
    ) -> dict[str, Any]:
        return await self.call(
            "foods.search.v3",
            {"search_expression": query},
            access_token=access_token,
            access_secret=access_secret,
        )


def _single(payload: Mapping[str, list[str]], key: str) -> str:
    values = payload.get(key)
    if not values or not values[0]:
        raise FatSecretClientError(f"FatSecret OAuth response omitted {key}.")
    return values[0]
