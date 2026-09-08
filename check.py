import asyncio

async def run_checks():
    print("1. Перевірка імпортів MCP...")
    from services.api.src.smart_basket.mcp.connection import get_mcp_session
    from services.api.src.smart_basket.mcp.adapters import get_purchase_history
    
    print("2. Перевірка імпортів маршрутів...")
    from services.api.src.smart_basket.routes.auth import silpo_oauth_callback
    
    print("3. Перевірка імпортів FatSecret...")
    from services.api.src.smart_basket.fatsecret.client import FatSecretClient
    from services.api.src.smart_basket.fatsecret.auth import get_fatsecret_auth_url
    
    print("\n✅ Усі файли успішно імпортовано! Синтаксичних помилок немає.")

if __name__ == "__main__":
    asyncio.run(run_checks())