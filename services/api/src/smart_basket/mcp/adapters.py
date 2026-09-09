import logging
import json
from typing import Any, Dict, List
import asyncio
from functools import wraps

logger = logging.getLogger(__name__)

class McpReadError(RuntimeError):
    """The provider read failed; this is different from a valid empty history."""

def with_retries(max_attempts=3, delay=1.0):
    """Повторює запит у разі тимчасової мережевої помилки чи Rate Limit."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    error_msg = str(e).lower()
                    # Критичні помилки авторизації не ретраїмо — відразу падаємо
                    if any(code in error_msg for code in ["401", "403", "unauthorized"]):
                        raise
                        
                    if attempt == max_attempts - 1:
                        logger.warning(f"Остаточна помилка у {func.__name__} після {max_attempts} спроб: {e}")
                        raise McpReadError(f"MCP read {func.__name__} failed after {max_attempts} attempts.") from e
                    
                    logger.warning(f"Спроба {attempt + 1} для {func.__name__} не вдалася: {e}. Повторення через {delay}с...")
                    await asyncio.sleep(delay)
        return wrapper
    return decorator

def _handle_adapter_exception(e: Exception, default_return: Any, context_name: str) -> Any:
    """Розділяє критичні помилки провайдера від штатної відсутності даних."""
    error_msg = str(e).lower()
    critical_indicators = ["401", "403", "429", "503", "unauthorized", "rate limit", "unavailable"]
    if any(indicator in error_msg for indicator in critical_indicators):
        logger.error(f"Критична помилка провайдера при отриманні ({context_name}): {e}")
        raise e
        
    logger.warning(f"Попередження при отриманні ({context_name}): {e}. Повертаємо безпечний дефолт.")
    return default_return

def _to_minor(value: Any) -> int:
    """Допоміжна функція: конвертує UAH у копійки для нормалізації."""
    try:
        return int(float(value) * 100)
    except (ValueError, TypeError):
        return 0

@with_retries(max_attempts=3)
async def get_user_profile(session) -> Dict[str, Any]:
    try:
        result = await session.call_tool("silpo_get_my_profile", arguments={})
        if result.content and len(result.content) > 0:
            return json.loads(result.content[0].text)
        return {}
    except Exception as e:
        return _handle_adapter_exception(e, {}, "профілю")

@with_retries(max_attempts=3)
async def get_family_info(session) -> Dict[str, Any]:
    try:
        result = await session.call_tool("silpo_get_my_family", arguments={})
        if result.content and len(result.content) > 0:
            return json.loads(result.content[0].text)
        return {}
    except Exception as e:
        return _handle_adapter_exception(e, {}, "даних сім'ї")

@with_retries(max_attempts=3)
async def get_purchase_history(session) -> List[Dict[str, Any]]:
    """Витягує онлайн та офлайн чеки (нормалізований список)."""
    history = []
    for tool_name, channel in (
        ("silpo_get_my_online_orders", "online"),
        ("silpo_get_my_offline_orders", "offline"),
    ):
        try:
            result = await session.call_tool(tool_name, arguments={})
            # Якщо контенту немає (порожня історія), ми не кидаємо помилку, а просто йдемо далі (вирішення пункту 4)
            if not result.content:
                continue
                
            decoded = json.loads(result.content[0].text)
            if isinstance(decoded, list):
                for order in decoded:
                    if isinstance(order, dict):
                        history.append({**order, "channel": order.get("channel", channel)})
        except Exception as e:
            logger.warning(f"Помилка отримання {channel} історії: {e}")
            continue
            
    return history

@with_retries(max_attempts=3)
async def search_products(session, query: str, branch_id: str) -> List[Dict[str, Any]]:
    """Шукає товари та повертає нормалізований формат (вирішення пункту 5)."""
    try:
        args = {"searchQuery": query, "branchId": branch_id}
        result = await session.call_tool("silpo_get_products", arguments=args)
        if result.content and len(result.content) > 0:
            raw_products = json.loads(result.content[0].text)
            # Мапимо сирі поля на ті, що вимагає контракт
            return [{
                "productId": str(p.get("id", p.get("productId", ""))),
                "title": p.get("name", p.get("title", "")),
                "currentPrice": _to_minor(p.get("price", p.get("currentPrice", 0))),
                "currency": "UAH",
                "unit": p.get("unit", ""),
                "availability": p.get("availability", False)
            } for p in raw_products]
        return []
    except Exception as e:
        return _handle_adapter_exception(e, [], f"пошуку товарів (query: {query})")

@with_retries(max_attempts=3)
async def get_food_restrictions(session) -> List[str]:
    try:
        result = await session.call_tool("silpo_get_my_food_restrictions", arguments={})
        if result.content and len(result.content) > 0:
            return json.loads(result.content[0].text)
        return []
    except Exception as e:
        return _handle_adapter_exception(e, [], "дієтичних обмежень")

@with_retries(max_attempts=3)
async def get_product_details(session, product_id: str, branch_id: str) -> Dict[str, Any]:
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
    try:
        result = await session.call_tool("silpo_get_promotions", arguments={"branchId": branch_id})
        if result.content and len(result.content) > 0:
            return json.loads(result.content[0].text)
        return []
    except Exception as e:
        return _handle_adapter_exception(e, [], "акцій магазину")

@with_retries(max_attempts=3)
async def get_favorites(session) -> List[Dict[str, Any]]:
    try:
        result = await session.call_tool("silpo_get_my_favorites", arguments={})
        if result.content and len(result.content) > 0:
            return json.loads(result.content[0].text)
        return []
    except Exception as e:
        return _handle_adapter_exception(e, [], "улюблених товарів")

@with_retries(max_attempts=3)
async def get_current_cart(session) -> Dict[str, Any]:
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