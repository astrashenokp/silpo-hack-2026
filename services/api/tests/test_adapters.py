import pytest
from unittest.mock import AsyncMock
from smart_basket.mcp.adapters import get_purchase_history, get_user_profile

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