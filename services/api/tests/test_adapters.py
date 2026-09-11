import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from smart_basket.core import Session
from smart_basket.mcp.adapters import (
    add_or_update_cart_products,
    cart_write_call,
    get_purchase_history,
    get_user_context,
    get_user_profile,
    normalize_product_search,
    product_search_call,
    product_write_metadata,
    search_products,
)


def test_product_write_metadata_retains_only_server_write_coordinates():
    payload = {"results": [{
        "productId": "milk-1",
        "companyId": "company-1",
        "branchId": "branch-1",
        "title": "Milk",
        "currentPrice": 42,
    }]}
    assert product_write_metadata(payload) == {
        "milk-1": {
            "productId": "milk-1",
            "companyId": "company-1",
            "branchId": "branch-1",
        }
    }


def test_cart_write_call_follows_live_tool_schema():
    schema = {
        "type": "object",
        "properties": {
            "products": {"type": "array", "items": {
                "type": "object",
                "properties": {
                    "productId": {"type": "string"},
                    "companyId": {"type": "string"},
                    "branchId": {"type": "string"},
                    "quantity": {"type": "number"},
                },
                "required": ["productId", "companyId", "branchId", "quantity"],
            }},
            "shoppingCartId": {"type": "string"},
            "deliveryType": {"type": "string"},
            "timeslotStart": {"type": "string"},
            "timeslotEnd": {"type": "string"},
        },
        "required": ["products", "shoppingCartId"],
    }
    assert cart_write_call(
        [{
            "productId": "milk-1",
            "companyId": "company-1",
            "branchId": "branch-1",
            "quantity": 2,
        }],
        "cart-1",
        "SelfPickup",
        {"start": "start", "end": "end"},
        schema,
    ) == ("silpo_add_or_update_cart_products", {
        "products": [{
            "productId": "milk-1",
            "companyId": "company-1",
            "branchId": "branch-1",
            "quantity": 2,
        }],
        "shoppingCartId": "cart-1",
        "deliveryType": "SelfPickup",
        "timeslotStart": "start",
        "timeslotEnd": "end",
    })


@pytest.mark.asyncio
async def test_cart_write_adapter_calls_provider_once():
    session = AsyncMock()
    session.call_tool.return_value = SimpleNamespace(
        is_error=False,
        structured_content={"success": True},
        content=[],
    )
    schema = {
        "type": "object",
        "properties": {
            "items": {"type": "array", "items": {
                "type": "object",
                "properties": {
                    "productId": {"type": "string"},
                    "quantity": {"type": "number"},
                },
                "required": ["productId", "quantity"],
            }},
            "cartId": {"type": "string"},
        },
        "required": ["items", "cartId"],
    }
    result = await add_or_update_cart_products(
        session,
        [{"productId": "milk-1", "quantity": 1}],
        cart_id="cart-1",
        delivery_type=None,
        timeslot=None,
        tool_schemas={"silpo_add_or_update_cart_products": schema},
    )
    assert result == {"success": True}
    session.call_tool.assert_awaited_once_with(
        "silpo_add_or_update_cart_products",
        arguments={
            "items": [{"productId": "milk-1", "quantity": 1}],
            "cartId": "cart-1",
        },
    )

@pytest.mark.asyncio
async def test_get_purchase_history_empty():
    """Перевіряємо, що успішна, але пуста відповідь повертає []"""
    mock_session = AsyncMock()
    # Симулюємо успішний виклик, але контент порожній
    mock_session.call_tool.return_value.content = []
    
    result = await get_purchase_history(mock_session)
    assert result == []

@pytest.mark.asyncio
async def test_get_purchase_history_auth_error():
    """Перевіряємо, що помилка 401 НЕ заковтується, а прокидається далі (raise)"""
    mock_session = AsyncMock()
    # Симулюємо падіння з помилкою 401 Unauthorized
    mock_session.call_tool.side_effect = Exception("401 Unauthorized: Invalid token")
    
    with pytest.raises(Exception) as exc_info:
        await get_purchase_history(mock_session)
    
    assert "401" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_user_context_reads_profile_history_and_cart_without_exposing_profile():
    payloads = {
        "silpo_get_my_profile": {"name": "Test User", "phone": "+380000000000"},
        "silpo_get_my_family": {
            "pets": [
                {"species": "cat", "count": 1},
                {"id": "pet-type-dog", "name": "", "slug": "dogs"},
            ],
        },
        "silpo_get_my_food_restrictions": {
            "restrictions": [{"slug": "peanut-free", "name": None}],
        },
        "silpo_get_my_online_orders": {"orders": [{"orderId": "online-1"}]},
        "silpo_get_my_offline_orders": {"orders": []},
        "silpo_get_my_shopping_cart": {"exists": True, "shoppingCartId": "cart-1"},
        "silpo_get_shopping_cart_by_id": {
            "shoppingCartId": "cart-1",
            "branchId": "branch-1",
            "deliveryType": "SelfPickup",
            "timeslot": {
                "start": "2026-09-10T12:00:00+03:00",
                "end": "2026-09-10T14:00:00+03:00",
            },
        },
    }

    calls = []

    class FakeSession:
        async def call_tool(self, name, arguments):
            calls.append((name, arguments))
            return SimpleNamespace(
                is_error=False,
                structured_content=payloads[name],
                content=[],
            )

    owner = Session("test-session")
    owner.silpo_tool_schemas["silpo_get_my_offline_orders"] = {
        "type": "object",
        "properties": {
            "branchId": {"type": "string"},
            "deliveryType": {"type": "string"},
            "timeslotStart": {"type": "string"},
            "timeslotEnd": {"type": "string"},
        },
        "required": ["branchId", "deliveryType", "timeslotStart", "timeslotEnd"],
    }
    context = await get_user_context(FakeSession(), owner)

    assert context.model_dump(by_alias=True) == {
        "preferences": [],
        "restrictions": ["peanut-free"],
        "pets": [
            {"species": "cat", "count": 1},
            {"species": "dog", "count": 1},
        ],
        "historyAvailable": True,
        "cartContextReady": True,
        "warnings": [],
    }
    assert "phone" not in context.model_dump_json()
    assert owner.silpo_cart_id == "cart-1"
    assert owner.silpo_branch_id == "branch-1"
    assert owner.silpo_delivery_type == "SelfPickup"
    assert ("silpo_get_my_offline_orders", {
        "branchId": "branch-1",
        "deliveryType": "SelfPickup",
        "timeslotStart": "2026-09-10T12:00:00+03:00",
        "timeslotEnd": "2026-09-10T14:00:00+03:00",
    }) in calls


def test_product_search_normalizes_money_package_and_unknown_restrictions():
    result = normalize_product_search({"products": [{
        "productId": "milk-1",
        "title": "Test milk",
        "currentPrice": "45.50",
        "regularPrice": 50,
        "unitOfMeasure": "package",
        "step": 1,
        "packageSize": "900 мл",
        "availability": True,
    }]}, "молоко")

    assert result.warnings == []
    assert len(result.products) == 1
    product = result.products[0]
    assert product.price_minor == 4550
    assert product.regular_price_minor == 5000
    assert product.content_quantity == 900
    assert product.content_unit == "ml"
    assert product.restriction_check == "unknown"
    assert product.source == "silpo"


def test_product_search_maps_real_silpo_weighted_fields():
    result = normalize_product_search({"products": [
        {
            "id": "packaged-1", "name": "Packaged milk", "price": 45.5,
            "oldPrice": 50, "step": 1, "available": True, "weighted": False,
        },
        {
            "id": "weighted-1", "name": "Weighted product", "price": 120,
            "step": 0.1, "available": True, "weighted": True,
        },
    ]}, "milk")

    assert result.warnings == []
    assert [product.selling_unit for product in result.products] == ["piece", "kg"]
    assert result.products[0].regular_price_minor == 5000
    assert result.products[1].quantity_step == 0.1
    assert result.products[1].content_quantity == 1000
    assert result.products[1].content_unit == "g"


def test_product_search_reads_explicit_package_weight_from_provider_name():
    result = normalize_product_search({"products": [{
        "id": "rice-1", "name": "Крупа рисова довгозерниста 1 кг",
        "price": 82.5, "step": 1, "available": True, "weighted": False,
    }]}, "рис")

    assert result.products[0].content_quantity == 1000
    assert result.products[0].content_unit == "g"


@pytest.mark.asyncio
async def test_product_search_calls_silpo_with_server_branch():
    session = AsyncMock()
    session.call_tool.return_value = SimpleNamespace(
        is_error=False,
        structured_content={"products": []},
        content=[],
    )

    schema = {
        "type": "object",
        "properties": {
            "products": {"type": "array", "items": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            }},
            "branchId": {"type": "string"},
        },
        "required": ["products", "branchId"],
    }
    result = await search_products(
        session,
        "rice",
        "branch-from-session",
        tool_schemas={"silpo_find_products_batch": schema},
    )

    assert result.query == "rice"
    session.call_tool.assert_awaited_once_with(
        "silpo_find_products_batch",
        arguments={"products": [{"query": "rice"}], "branchId": "branch-from-session"},
    )


def test_product_search_call_follows_live_tool_schema():
    schema = {
        "type": "object",
        "properties": {
            "items": {"type": "array", "items": {
                "type": "object",
                "properties": {"name": {"type": "string"}, "quantity": {"type": "number"}},
                "required": ["name", "quantity"],
            }},
            "shoppingCartId": {"type": "string"},
            "deliveryType": {"type": "string"},
            "timeslotStart": {"type": "string"},
            "page": {"type": "integer", "default": 1},
        },
        "required": ["items", "shoppingCartId", "deliveryType", "timeslotStart", "page"],
    }
    assert product_search_call(
        "milk",
        "unused-branch",
        "cart-1",
        "SelfPickup",
        {"start": "2026-09-10T12:00:00+03:00"},
        {"silpo_find_products_batch": schema},
    ) == ("silpo_find_products_batch", {
        "items": [{"name": "milk", "quantity": 1}],
        "shoppingCartId": "cart-1",
        "deliveryType": "SelfPickup",
        "timeslotStart": "2026-09-10T12:00:00+03:00",
    })
