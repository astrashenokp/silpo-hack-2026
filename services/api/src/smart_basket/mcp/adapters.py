import logging
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, List, Mapping
import asyncio
from functools import wraps

from smart_basket.schemas import Pet, Purchase, UserContext

logger = logging.getLogger(__name__)

class McpReadError(RuntimeError):
    """The provider read failed; this is different from a valid empty history."""

@dataclass(frozen=True)
class PurchaseHistoryResult:
    purchases: list[dict[str, Any]]
    warnings: list[str]


def _decode_tool_payload(result: Any, default: Any) -> Any:
    """Prefer MCP structured content and fall back to a JSON text block."""
    if getattr(result, "is_error", False):
        message = next(
            (item.text for item in getattr(result, "content", []) if getattr(item, "text", None)),
            "Silpo MCP tool returned an error.",
        )
        raise McpReadError(message)
    structured = getattr(result, "structured_content", None)
    if structured is not None:
        return structured
    for item in getattr(result, "content", []):
        text = getattr(item, "text", None)
        if text:
            return json.loads(text)
    return default


def _list_payload(payload: Any, *keys: str) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, list):
                return value
        for value in payload.values():
            found = _list_payload(value, *keys)
            if found:
                return found
    return []


def _find_value(payload: Any, *keys: str) -> Any:
    """Find a provider field without exposing or copying the full provider response."""
    if isinstance(payload, dict):
        for key in keys:
            if payload.get(key) is not None:
                return payload[key]
        for value in payload.values():
            found = _find_value(value, *keys)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for value in payload:
            found = _find_value(value, *keys)
            if found is not None:
                return found
    return None


def _string_values(payload: Any, *keys: str) -> list[str]:
    values = _list_payload(payload, *keys)
    return list(dict.fromkeys(value for value in values if isinstance(value, str) and value))


def _normalize_pets(payload: Any) -> list[Pet]:
    raw_pets = _list_payload(payload, "pets", "animals")
    counts: dict[str, int] = {}
    aliases = {"cat": "cat", "кіт": "cat", "кішка": "cat", "dog": "dog", "пес": "dog", "собака": "dog"}
    for item in raw_pets:
        if not isinstance(item, dict):
            continue
        raw_species = item.get("species") or item.get("type") or item.get("animalType")
        species = aliases.get(str(raw_species).strip().lower())
        if species is None:
            continue
        raw_count = item.get("count", 1)
        if isinstance(raw_count, bool) or not isinstance(raw_count, int) or raw_count < 1:
            continue
        counts[species] = counts.get(species, 0) + raw_count
    return [Pet(species=species, count=count) for species, count in sorted(counts.items())]

def uah_to_minor(value: Any) -> int:
    """Convert a UAH value to integer kopiykas without binary-float rounding."""
    if isinstance(value, bool):
        raise ValueError("A boolean is not a money value.")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("Invalid UAH money value.") from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError("UAH money value must be finite and non-negative.")
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

def normalize_purchase_history(
    raw_orders: list[dict[str, Any]] | None,
    *,
    product_metadata: Mapping[str, Mapping[str, Any]] | None = None,
    default_channel: str | None = None,
) -> PurchaseHistoryResult:
    """Flatten provider orders into the contract consumed by Vika."""
    if raw_orders is None:
        raise McpReadError("Silpo purchase history is unavailable.")
    if not isinstance(raw_orders, list):
        raise McpReadError("Silpo purchase history returned an invalid shape.")

    metadata = product_metadata or {}
    purchases: list[dict[str, Any]] = []
    warnings: list[str] = []
    seen: set[tuple[str, str, str]] = set()

    for order_index, order in enumerate(raw_orders):
        if not isinstance(order, dict):
            warnings.append(f"Skipped order {order_index}: expected an object.")
            continue
        receipt_id = order.get("receiptId") or order.get("orderId")
        purchased_at = order.get("purchasedAt") or order.get("date")
        channel = order.get("channel") or default_channel
        items = order.get("items")
        if not receipt_id or not purchased_at or channel not in {"online", "offline"}:
            warnings.append(f"Skipped order {order_index}: receipt, timestamp or channel is unresolved.")
            continue
        if not isinstance(items, list):
            warnings.append(f"Skipped order {receipt_id}: items are unavailable.")
            continue

        for item_index, item in enumerate(items):
            if not isinstance(item, dict):
                warnings.append(f"Skipped item {item_index} in receipt {receipt_id}: expected an object.")
                continue
            product_id = item.get("productId")
            details = metadata.get(str(product_id), {}) if product_id is not None else {}
            name = item.get("name") or details.get("name")
            category = item.get("category") or details.get("category")
            unit = item.get("unit") or details.get("unit")
            quantity = item.get("quantity")
            missing = [key for key, value in {
                "productId": product_id, "name": name, "category": category,
                "quantity": quantity, "unit": unit,
            }.items() if value is None or value == ""]
            if missing:
                warnings.append(
                    f"Skipped item {item_index} in receipt {receipt_id}: unresolved {', '.join(missing)}."
                )
                continue

            price_minor = item.get("priceMinor")
            if price_minor is not None:
                if isinstance(price_minor, bool) or not isinstance(price_minor, int) or price_minor < 0:
                    warnings.append(f"Skipped item {item_index} in receipt {receipt_id}: invalid priceMinor.")
                    continue
            elif item.get("price") is not None:
                try:
                    price_minor = uah_to_minor(item["price"])
                except ValueError:
                    warnings.append(f"Skipped item {item_index} in receipt {receipt_id}: invalid UAH price.")
                    continue

            dedup_key = (str(receipt_id), str(product_id), str(item.get("lineId", product_id)))
            if dedup_key in seen:
                warnings.append(f"Skipped duplicate product {product_id} in receipt {receipt_id}.")
                continue
            try:
                purchase = Purchase(
                    receipt_id=str(receipt_id), purchased_at=str(purchased_at), channel=channel,
                    product_id=str(product_id), name=str(name), category=str(category),
                    quantity=float(quantity), unit=str(unit), unit_price_minor=price_minor,
                )
            except (TypeError, ValueError):
                warnings.append(f"Skipped item {item_index} in receipt {receipt_id}: invalid normalized values.")
                continue
            seen.add(dedup_key)
            purchases.append(purchase.model_dump(by_alias=True))

    return PurchaseHistoryResult(purchases=purchases, warnings=warnings)

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
        payload = _decode_tool_payload(result, {})
        return payload if isinstance(payload, dict) else {}
    except Exception as e:
        return _handle_adapter_exception(e, {}, "профілю")

@with_retries(max_attempts=3)
async def get_family_info(session) -> Dict[str, Any]:
    try:
        result = await session.call_tool("silpo_get_my_family", arguments={})
        payload = _decode_tool_payload(result, {})
        return payload if isinstance(payload, dict) else {}
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
            decoded = _decode_tool_payload(result, [])
            for order in _list_payload(decoded, "orders", "items", "data"):
                if isinstance(order, dict):
                    history.append({**order, "channel": order.get("channel", channel)})
        except Exception as e:
            _handle_adapter_exception(e, None, f"{channel} історії")
            continue
            
    return history

async def get_normalized_purchase_history(
    session,
    *,
    product_metadata: Mapping[str, Mapping[str, Any]] | None = None,
) -> PurchaseHistoryResult:
    """Read Silpo history and return Vika-compatible normalized purchases."""
    raw_orders = await get_purchase_history(session)
    return normalize_purchase_history(raw_orders, product_metadata=product_metadata)

@with_retries(max_attempts=3)
async def search_products(session, query: str, branch_id: str) -> List[Dict[str, Any]]:
    """Шукає товари та повертає нормалізований формат."""
    try:
        args = {"searchQuery": query, "branchId": branch_id}
        result = await session.call_tool("silpo_get_products", arguments=args)
        if result.content and len(result.content) > 0:
            raw_products = json.loads(result.content[0].text)
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
async def get_food_restrictions(session) -> Any:
    try:
        result = await session.call_tool("silpo_get_my_food_restrictions", arguments={})
        return _decode_tool_payload(result, [])
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
        cart_data = _decode_tool_payload(cart_info, {})
        if not isinstance(cart_data, dict):
            return {}
        cart_id = _find_value(cart_data, "shoppingCartId", "cartId")
        if _find_value(cart_data, "exists") is False or cart_id is None:
            return cart_data

        details = await session.call_tool("silpo_get_shopping_cart_by_id", arguments={"shoppingCartId": cart_id})
        
        cart_details = _decode_tool_payload(details, {})
        if isinstance(cart_details, dict):
            return {**cart_data, **cart_details}
        return cart_data
    except Exception as e:
        return _handle_adapter_exception(e, {}, "поточного кошика")


async def get_user_context(session, owner=None) -> UserContext:
    """Build the public context while retaining private cart coordinates server-side."""
    profile = await get_user_profile(session)
    family = await get_family_info(session)
    food = await get_food_restrictions(session)
    history = await get_purchase_history(session)
    cart = await get_current_cart(session)

    preferences = _string_values(food, "preferences", "foodPreferences")
    restrictions = _string_values(food, "restrictions", "foodRestrictions")
    if isinstance(food, list):
        restrictions = _string_values(food)
    pets = _normalize_pets(family)

    cart_id = _find_value(cart, "shoppingCartId", "cartId")
    branch_id = _find_value(cart, "branchId")
    delivery_type = _find_value(cart, "deliveryType")
    timeslot = _find_value(cart, "timeslot", "timeSlot")
    cart_ready = all((cart_id, branch_id, delivery_type, timeslot))

    warnings: list[str] = []
    if not profile:
        warnings.append("Silpo profile returned no data.")
    if not history:
        warnings.append("Silpo purchase history is empty.")
    if not cart_id:
        warnings.append("Silpo has no active shopping cart.")
    elif not cart_ready:
        warnings.append("Silpo cart exists, but its store or delivery context is incomplete.")

    if owner is not None:
        with owner.lock:
            owner.silpo_cart_id = str(cart_id) if cart_id is not None else None
            owner.silpo_branch_id = str(branch_id) if branch_id is not None else None
            owner.silpo_delivery_type = str(delivery_type) if delivery_type is not None else None
            owner.silpo_timeslot = timeslot

    return UserContext(
        preferences=preferences,
        restrictions=restrictions,
        pets=pets,
        history_available=bool(history),
        cart_context_ready=cart_ready,
        warnings=warnings,
    )
