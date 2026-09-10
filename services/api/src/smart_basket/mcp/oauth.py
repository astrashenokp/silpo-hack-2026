"""Browser OAuth coordination for the Silpo MCP client."""

import asyncio
import os
from contextlib import suppress
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from mcp.client.auth import OAuthFlowError
from mcp.shared.auth import AuthorizationCodeResult

from smart_basket.mcp.connection import SessionTokenStorage, get_mcp_session


class SilpoOAuthError(RuntimeError):
    """The browser authorization could not be completed."""


class SilpoOAuthFlow:
    def __init__(self, owner):
        self.owner = owner
        loop = asyncio.get_running_loop()
        self.authorization_url: asyncio.Future[str] = loop.create_future()
        self.callback: asyncio.Future[AuthorizationCodeResult] = loop.create_future()
        self.task = asyncio.create_task(self._connect())

    async def _redirect(self, authorization_url: str) -> None:
        if not self.authorization_url.done():
            self.authorization_url.set_result(authorization_url)

    async def _callback(self) -> AuthorizationCodeResult:
        return await self.callback

    async def _connect(self) -> None:
        storage = SessionTokenStorage(self.owner)
        async with get_mcp_session(
            storage,
            redirect_handler=self._redirect,
            callback_handler=self._callback,
        ) as session:
            result = await session.list_tools()
            tools = tuple(tool.name for tool in result.tools)
        with self.owner.lock:
            self.owner.silpo_connected = True
            self.owner.silpo_tools = tools

    async def wait_for_authorization_url(self) -> str | None:
        done, _ = await asyncio.wait(
            {self.authorization_url, self.task},
            timeout=30,
            return_when=asyncio.FIRST_COMPLETED,
        )
        if self.authorization_url in done:
            return self.authorization_url.result()
        if self.task in done:
            self.task.result()
            return None
        await self.cancel()
        raise SilpoOAuthError("Silpo did not provide an authorization URL in time.")

    async def cancel(self) -> None:
        if not self.task.done():
            self.task.cancel()
            with suppress(asyncio.CancelledError):
                await self.task

    async def finish(self, *, code: str, state: str, iss: str | None) -> None:
        if self.task.done():
            self.task.result()
            raise SilpoOAuthError("The Silpo authorization flow is no longer pending.")
        if self.callback.done():
            raise SilpoOAuthError("The Silpo callback was already received.")
        self.callback.set_result(AuthorizationCodeResult(code=code, state=state, iss=iss))
        try:
            await asyncio.wait_for(asyncio.shield(self.task), timeout=30)
        except TimeoutError as exc:
            await self.cancel()
            raise SilpoOAuthError("Silpo token exchange timed out.") from exc
        except OAuthFlowError as exc:
            raise SilpoOAuthError("Silpo rejected the OAuth exchange.") from exc


class SilpoOAuthManager:
    async def start(self, owner) -> str:
        with owner.lock:
            if owner.silpo_connected:
                return self.return_url(connected=True)
            current = owner.silpo_auth_flow
            if current is None or current.task.done():
                current = SilpoOAuthFlow(owner)
                owner.silpo_auth_flow = current
        try:
            authorization_url = await current.wait_for_authorization_url()
            return authorization_url or self.return_url(connected=True)
        except Exception:
            with owner.lock:
                if owner.silpo_auth_flow is current:
                    owner.silpo_auth_flow = None
            raise

    async def cancel(self, owner) -> None:
        with owner.lock:
            current = owner.silpo_auth_flow
            owner.silpo_auth_flow = None
        if current is not None:
            await current.cancel()

    async def finish(self, owner, *, code: str, state: str, iss: str | None) -> None:
        with owner.lock:
            current = owner.silpo_auth_flow
        if current is None:
            raise SilpoOAuthError("No Silpo authorization is pending for this session.")
        try:
            await current.finish(code=code, state=state, iss=iss)
        finally:
            with owner.lock:
                if owner.silpo_auth_flow is current:
                    owner.silpo_auth_flow = None

    def return_url(self, *, connected: bool) -> str:
        target = os.getenv("SMART_BASKET_FRONTEND_URL", "http://localhost:3000")
        parts = urlsplit(target)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query["silpo"] = "connected" if connected else "error"
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
