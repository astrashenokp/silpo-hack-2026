import logging
import json
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

async def get_user_profile(session) -> Dict[str, Any]:
    #Витягує дані профілю (ім'я, телефон, дата народження).
    try:
        result = await session.call_tool("silpo_get_my_profile", arguments={})
        if result.content and len(result.content) > 0:
            return json.loads(result.content[0].text)
        return {}
    except Exception as e:
        logger.warning(f"Помилка отримання профілю: {e}")
        return {}  #Якщо помилка - просто віддаємо пустий словник

async def get_family_info(session) -> Dict[str, Any]:
    #Витягує дані про сім'ю та тварин (для підбору товарів).
    try:
        result = await session.call_tool("silpo_get_my_family", arguments={})
        if result.content and len(result.content) > 0:
            return json.loads(result.content[0].text)
        return {}
    except Exception as e:
        logger.warning(f"Помилка отримання сім'ї: {e}")
        return {}

async def get_purchase_history(session) -> List[Dict[str, Any]]:
    #Витягує онлайн та офлайн чеки.
    history = []
    try:
        # Спочатку беремо онлайн замовлення
        online = await session.call_tool("silpo_get_my_online_orders", arguments={})
        if online.content and len(online.content) > 0:
            history.extend(json.loads(online.content[0].text))
            
        # Потім офлайн чеки з магазину
        offline = await session.call_tool("silpo_get_my_offline_orders", arguments={})
        if offline.content and len(offline.content) > 0:
            history.extend(json.loads(offline.content[0].text))
            
        return history
    except Exception as e:
        logger.warning(f"Помилка отримання історії покупок: {e}")
        return []  # Якщо чеків нема, віддаємо пустий список

async def search_products(session, query: str, branch_id: str) -> Dict[str, Any]:
    #Шукає товари за запитом у конкретному магазині.
    try:
        args = {"searchQuery": query, "branchId": branch_id}
        result = await session.call_tool("silpo_get_products", arguments=args)
        if result.content and len(result.content) > 0:
            return json.loads(result.content[0].text)
        return {}
    except Exception as e:
        logger.warning(f"Помилка пошуку товарів: {e}")
        return {}