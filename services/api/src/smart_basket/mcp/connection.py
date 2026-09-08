from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
import logging

logger = logging.getLogger(__name__)

async def get_mcp_session(mcp_token: str) -> ClientSession:
    #з'єднання з MCP Сільпо
    my_oauth_provider = {"Authorization": f"Bearer {mcp_token}"}
    
    try:
        async with streamablehttp_client(
            "https://mcp.silpo.ua/mcp",
            auth=my_oauth_provider,
        ) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                logger.info("MCP Session initialized successfully")
                return session
    except Exception as e:
        logger.error(f"Failed to connect to Silpo MCP: {e}")
        raise