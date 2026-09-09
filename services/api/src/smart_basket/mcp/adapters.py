import logging
import json
from typing import Any, Dict, List
import asyncio
from functools import wraps

logger = logging.getLogger(__name__)

def with_retries(max_attempts=3, delay=1.0):
    #Повторює запит у разі тимчасової мережевої помилки чи Rate Limit.
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    error_msg = str(e).lower()
                    #Критичні помилки авторизації не ретраїмо — відразу падаємо
                    if any(code in error_msg for code in ["401", "403", "unauthorized"]):
                        raise
                        
                    if attempt == max_attempts - 1:
                        logger.error(f"Остаточна помилка у {func.__name__} після {max_attempts} спроб: {e}")
                        # Якщо це функція історії чи списків — повертаємо [], інакше {}
                        return [] if any(k in func.__name__ for k in ["history", "restrictions", "promotions", "favorites"]) else {}
                    
                    logger.warning(f"Спроба {attempt + 1} для {func.__name__} не вдалася: {e}. Повторення через {delay}с...")
                    await asyncio.sleep(delay)
        return wrapper
    return decorator


def _handle_adapter_exception(e: Exception, default_return: Any, context_name: str) -> Any:
    #Розділяє критичні помилки провайдера (які мають підняти виняток) від штатної відсутності даних або порожніх відповідей.
    error_msg = str(e).lower()
    
    # Критичні помилки: відсутність доступу, ліміти, недоступність сервісу
    critical_indicators = ["401", "403", "429", "503", "unauthorized", "rate limit", "unavailable"]
    if any(indicator in error_msg for indicator in critical_indicators):
        logger.error(f"Критична помилка провайдера при отриманні ({context_name}): {e}")
        raise e
        
    # Штатна ситуація / звичайна бізнес-помилка — повертаємо безпечний дефолт
    logger.warning(f"Попередження при отриманні ({context_name}): {e}. Повертаємо порожню структуру.")
    return default_return


@with_retries(max_attempts=3)
async def get_user_profile(session) -> Dict[str, Any]:
    #Витягує дані профілю (ім'я, телефон, дата народження).
    try:
        result = await session.call_tool("silpo_get_my_profile", arguments={})
        if result.content and len(result.content) > 0:
            return json.loads(result.content[0].text)
        return {}
    except Exception as e:
        return _handle_adapter_exception(e, {}, "профілю")


@with_retries(max_attempts=3)
async def get_family_info(session) -> Dict[str, Any]:
    #Витягує дані про сім'ю та тварин (для підбору товарів).
    try:
        result = await session.call_tool("silpo_get_my_family", arguments={})
        if result.content and len(result.content) > 0:
            return json.loads(result.content[0].text)
        return {}
    except Exception as e:
        return _handle_adapter_exception(e, {}, "даних сім'ї")


@with_retries(max_attempts=3)
async def get_purchase_history(session) -> List[Dict[str, Any]]:
    #Витягує онлайн та офлайн чеки (нормалізований список).
    history = []
    try:
        # Онлайн замовлення
        online = await session.call_tool("silpo_get_my_online_orders", arguments={})
        if online.content and len(online.content) > 0:
            history.extend(json.loads(online.content[0].text))
            
        # Офлайн чеки з магазину
        offline = await session.call_tool("silpo_get_my_offline_orders", arguments={})
        if offline.content and len(offline.content) > 0:
            history.extend(json.loads(offline.content[0].text))
            
        return history
    except Exception as e:
        return _handle_adapter_exception(e, [], "історії покупок")


@with_retries(max_attempts=3)
async def search_products(session, query: str, branch_id: str) -> Dict[str, Any]:
    #Шукає товари за запитом у конкретному магазині за branchId.
    try:
        args = {"searchQuery": query, "branchId": branch_id}
        result = await session.call_tool("silpo_get_products", arguments=args)
        if result.content and len(result.content) > 0:
            return json.loads(result.content[0].text)
        return {}
    except Exception as e:
        return _handle_adapter_exception(e, {}, f"пошуку товарів (query: {query})")


@with_retries(max_attempts=3)
async def get_food_restrictions(session) -> List[str]:
    #Витягує дієтичні обмеження гостя.
    try:
        result = await session.call_tool("silpo_get_my_food_restrictions", arguments={})
        if result.content and len(result.content) > 0:
            return json.loads(result.content[0].text)
        return []
    except Exception as e:
        return _handle_adapter_exception(e, [], "дієтичних обмежень")


@with_retries(max_attempts=3)
async def get_product_details(session, product_id: str, branch_id: str) -> Dict[str, Any]:
    #Отримує повну картку товару (склад, харчова цінність, розмір упаковки).
    try:
        args = {"productId": product_id, "branchId": branch_id}
        result = await session.call_tool("silpo_get_product_details", arguments=args)
        if result.content and len(result.content) > 0:
            return json.loads(result.content[0].text)
        return {}
    except Exception as e:
        return _handle_adapter_exception(e, {}, f"деталей товару {product_id}")


@with_retries(max_attempts=3)
async def get_promotions(session, branch_id: str) -> List[Dict[str, Any]]:
    #Отримує активні акції в магазині за branchId.
    try:
        result = await session.call_tool("silpo_get_promotions", arguments={"branchId": branch_id})
        if result.content and len(result.content) > 0:
            return json.loads(result.content[0].text)
        return []
    except Exception as e:
        return _handle_adapter_exception(e, [], "акцій магазину")


@with_retries(max_attempts=3)
async def get_favorites(session) -> List[Dict[str, Any]]:
    #Список збережених улюблених товарів гостя.
    try:
        result = await session.call_tool("silpo_get_my_favorites", arguments={})
        if result.content and len(result.content) > 0:
            return json.loads(result.content[0].text)
        return []
    except Exception as e:
        return _handle_adapter_exception(e, [], "улюблених товарів")


@with_retries(max_attempts=3)
async def get_current_cart(session) -> Dict[str, Any]:
    #Отримує поточний кошик гостя (включно зі створенням/отриманням shoppingCartId).
    try:
        cart_info = await session.call_tool("silpo_get_my_shopping_cart", arguments={})
        if not cart_info.content:
            return {}
            
        cart_data = json.loads(cart_info.content[0].text)
        if not cart_data.get("exists") or not cart_data.get("shoppingCartId"):
            return {}
            
        cart_id = cart_data["shoppingCartId"]
        details = await session.call_tool("silpo_get_shopping_cart_by_id", arguments={"shoppingCartId": cart_id})
        
        if details.content and len(details.content) > 0:
            return json.loads(details.content[0].text)
        return {}
    except Exception as e:
        return _handle_adapter_exception(e, {}, "поточного кошика")