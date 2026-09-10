import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from smart_basket.core import Session
from smart_basket.mcp.adapters import get_purchase_history, get_user_context, get_user_profile

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
        "silpo_get_my_family": {"pets": [{"species": "cat", "count": 1}]},
        "silpo_get_my_food_restrictions": {
            "preferences": ["vegetarian"],
            "restrictions": ["peanut-free"],
        },
        "silpo_get_my_online_orders": {"orders": [{"orderId": "online-1"}]},
        "silpo_get_my_offline_orders": {"orders": []},
        "silpo_get_my_shopping_cart": {"exists": True, "shoppingCartId": "cart-1"},
        "silpo_get_shopping_cart_by_id": {
            "shoppingCartId": "cart-1",
            "branchId": "branch-1",
            "deliveryType": "SelfPickup",
            "timeslot": {"start": "2026-09-10T12:00:00+03:00"},
        },
    }

    class FakeSession:
        async def call_tool(self, name, arguments):
            return SimpleNamespace(
                is_error=False,
                structured_content=payloads[name],
                content=[],
            )

    owner = Session("test-session")
    context = await get_user_context(FakeSession(), owner)

    assert context.model_dump(by_alias=True) == {
        "preferences": ["vegetarian"],
        "restrictions": ["peanut-free"],
        "pets": [{"species": "cat", "count": 1}],
        "historyAvailable": True,
        "cartContextReady": True,
        "warnings": [],
    }
    assert "phone" not in context.model_dump_json()
    assert owner.silpo_cart_id == "cart-1"
    assert owner.silpo_branch_id == "branch-1"
    assert owner.silpo_delivery_type == "SelfPickup"
