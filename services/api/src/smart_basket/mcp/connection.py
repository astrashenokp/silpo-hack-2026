from mcp import ClientSession
from mcp.client.sse import sse_client
import logging

logger = logging.getLogger(__name__)

async def get_mcp_session(mcp_token: str) -> ClientSession:
    """Встановлює з'єднання з офіційним MCP Сільпо."""
    headers = {"Authorization": f"Bearer {mcp_token}"}
    
    try:
        # Використовуємо актуальний sse_client замість застарілого streamablehttp_client
        async with sse_client(
            "https://mcp.silpo.ua/mcp",
            headers=headers,
        ) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                logger.info("MCP Session initialized successfully")
                return session
    except Exception as e:
        logger.error(f"Failed to connect to Silpo MCP: {e}")
        raise