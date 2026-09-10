"""Authenticated Streamable HTTP connection to the official Silpo MCP server."""

import os
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

import httpx2
from mcp import ClientSession
from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import (
    AuthorizationCodeResult,
    OAuthClientInformationFull,
    OAuthClientMetadata,
    OAuthToken,
)
from pydantic import AnyUrl


class SessionTokenStorage(TokenStorage):
    """Keep OAuth tokens and the dynamic client registration in a server session."""

    def __init__(self, owner: Any):
        self.owner = owner

    async def get_tokens(self) -> OAuthToken | None:
        with self.owner.lock:
            return self.owner.silpo_tokens

    async def set_tokens(self, tokens: OAuthToken) -> None:
        with self.owner.lock:
            self.owner.silpo_tokens = tokens

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        with self.owner.lock:
            return self.owner.silpo_client_info

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        with self.owner.lock:
            self.owner.silpo_client_info = client_info


def silpo_mcp_url() -> str:
    return os.getenv("SILPO_MCP_URL", "https://mcp.silpo.ua/mcp")


def silpo_callback_url() -> str:
    return os.getenv(
        "SILPO_OAUTH_CALLBACK_URL",
        "http://localhost:8000/api/auth/silpo/callback",
    )


@asynccontextmanager
async def get_mcp_session(
    storage: TokenStorage,
    *,
    redirect_handler: Callable[[str], Awaitable[None]] | None = None,
    callback_handler: Callable[[], Awaitable[AuthorizationCodeResult]] | None = None,
):
    """Open an MCP session; the SDK handles discovery, DCR, PKCE and refresh."""

    endpoint = silpo_mcp_url()
    oauth = OAuthClientProvider(
        server_url=endpoint,
        client_metadata=OAuthClientMetadata(
            client_name="Smart Basket",
            software_version="0.2.0",
            redirect_uris=[AnyUrl(silpo_callback_url())],
            application_type="web",
            token_endpoint_auth_method="none",
        ),
        storage=storage,
        redirect_handler=redirect_handler,
        callback_handler=callback_handler,
    )
    async with httpx2.AsyncClient(auth=oauth, follow_redirects=True) as http_client:
        async with streamable_http_client(endpoint, http_client=http_client) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session
