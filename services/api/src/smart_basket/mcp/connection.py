from contextlib import asynccontextmanager
from mcp import ClientSession
from mcp.client.sse import sse_client
import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def get_mcp_session(mcp_token: str):
    #Контекстний менеджер для безпечного керування життєвим циклом MCP сесії.
    headers = {"Authorization": f"Bearer {mcp_token}"}
    async with sse_client("https://mcp.silpo.ua/mcp", headers=headers) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            logger.info("MCP Session initialized and active")
            yield session