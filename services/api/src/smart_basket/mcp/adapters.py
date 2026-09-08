import logging
import json
from typing import Any, Dict, List
import asyncio
from functools import wraps

logger = logging.getLogger(__name__)

def with_retries(max_attempts=3, delay=1.0):
    """Повторює запит у разі тимчасової помилки мережі."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        logger.warning(f"Остаточна помилка у {func.__name__} після {max_attempts} спроб: {e}")
                        return [] if "history" in func.__name__ else {}
                    await asyncio.sleep(delay)
        return wrapper
    return decorator

async def get_user_profile(session) -> Dict[str, Any]:
    """Витягує дані профілю (ім'я, телефон, дата народження)."""
    try:
        result = await session.call_tool("silpo_get_my_profile", arguments={})
        if result.content and len(result.content) > 0:
            return json.loads(result.content[0].text)
        return {}
    except Exception as e:
        logger.warning(f"Помилка отримання профілю: {e}")
        return {}  # Якщо помилка - просто віддаємо пустий словник

async def get_family_info(session) -> Dict[str, Any]:
    """Витягує дані про сім'ю та тварин (для підбору товарів)."""
    try:
        result = await session.call_tool("silpo_get_my_family", arguments={})
        if result.content and len(result.content) > 0:
            return json.loads(result.content[0].text)
        return {}
    except Exception as e:
        logger.warning(f"Помилка отримання сім'ї: {e}")
        return {}

@with_retries(max_attempts=3)
async def get_purchase_history(session) -> List[Dict[str, Any]]:
    """Витягує онлайн та офлайн чеки."""
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
    """Шукає товари за запитом у конкретному магазині."""
    try:
        args = {"searchQuery": query, "branchId": branch_id}
        result = await session.call_tool("silpo_get_products", arguments=args)
        if result.content and len(result.content) > 0:
            return json.loads(result.content[0].text)
        return {}
    except Exception as e:
        logger.warning(f"Помилка пошуку товарів: {e}")
        return {}

async def get_food_restrictions(session) -> List[str]:
    """Витягує дієтичні обмеження гостя."""
    try:
        result = await session.call_tool("silpo_get_my_food_restrictions", arguments={})
        if result.content and len(result.content) > 0:
            return json.loads(result.content[0].text)
        return []
    except Exception as e:
        logger.warning(f"Помилка отримання обмежень: {e}")
        return []

async def get_product_details(session, product_id: str, branch_id: str) -> Dict[str, Any]:
    """Отримує повну картку товару (склад, харчова цінність)."""
    try:
        args = {"productId": product_id, "branchId": branch_id}
        result = await session.call_tool("silpo_get_product_details", arguments=args)
        if result.content and len(result.content) > 0:
            return json.loads(result.content[0].text)
        return {}
    except Exception as e:
        logger.warning(f"Помилка отримання деталей товару {product_id}: {e}")
        return {}

async def get_promotions(session, branch_id: str) -> List[Dict[str, Any]]:
    """Отримує активні акції в магазині."""
    try:
        result = await session.call_tool("silpo_get_promotions", arguments={"branchId": branch_id})
        if result.content and len(result.content) > 0:
            return json.loads(result.content[0].text)
        return []
    except Exception as e:
        logger.warning(f"Помилка отримання акцій: {e}")
        return []

async def get_favorites(session) -> List[Dict[str, Any]]:
    """Список збережених улюблених товарів гостя."""
    try:
        result = await session.call_tool("silpo_get_my_favorites", arguments={})
        if result.content and len(result.content) > 0:
            return json.loads(result.content[0].text)
        return []
    except Exception as e:
        logger.warning(f"Помилка отримання улюблених товарів: {e}")
        return []

async def get_current_cart(session) -> Dict[str, Any]:
    """Отримує поточний кошик гостя."""
    try:
        # Спочатку дізнаємося ID кошика
        cart_info = await session.call_tool("silpo_get_my_shopping_cart", arguments={})
        if not cart_info.content:
            return {}
            
        cart_data = json.loads(cart_info.content[0].text)
        if not cart_data.get("exists") or not cart_data.get("shoppingCartId"):
            return {}
            
        # Якщо кошик є, тягнемо його деталі
        cart_id = cart_data["shoppingCartId"]
        details = await session.call_tool("silpo_get_shopping_cart_by_id", arguments={"shoppingCartId": cart_id})
        
        if details.content and len(details.content) > 0:
            return json.loads(details.content[0].text)
        return {}
    except Exception as e:
        logger.warning(f"Помилка отримання кошика: {e}")
        return {}