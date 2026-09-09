import asyncio
import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from smart_basket.mcp.adapters import (
    McpReadError,
    get_normalized_purchase_history,
    normalize_purchase_history,
    uah_to_minor,
)
from smart_basket.optimization.recurrence import analyze_recurring
from smart_basket.schemas import Pet, Purchase

ROOT = Path(__file__).resolve().parents[3]


def test_raw_fixture_normalizes_to_public_purchase_contract():
    raw = json.loads((ROOT / "fixtures/silpo-purchase-history-raw.json").read_text(encoding="utf-8"))
    result = normalize_purchase_history(raw, default_channel="online", product_metadata={
        "p-001": {"category": "dairy", "unit": "piece"},
        "p-002": {"category": "eggs", "unit": "package"},
    })
    assert result.warnings == []
    assert len(result.purchases) == 2
    first = Purchase.model_validate(result.purchases[0])
    assert first.receipt_id == "12345"
    assert first.channel == "online"
    assert first.unit_price_minor == 4550


def test_empty_history_and_provider_failure_are_distinct():
    assert normalize_purchase_history([]).purchases == []
    with pytest.raises(McpReadError, match="unavailable"):
        normalize_purchase_history(None)


@pytest.mark.parametrize("value,expected", [(45.50, 4550), ("45.505", 4551), (0, 0)])
def test_uah_prices_are_rounded_to_kopiykas(value, expected):
    assert uah_to_minor(value) == expected


def test_unresolved_product_metadata_is_reported_not_invented():
    raw = [{"orderId": "r1", "date": "2026-09-01T10:00:00Z", "channel": "online",
            "items": [{"productId": "p1", "name": "Unknown", "quantity": 1}]}]
    result = normalize_purchase_history(raw)
    assert result.purchases == []
    assert "category, unit" in result.warnings[0]


def test_normalized_history_is_accepted_by_vika():
    raw = [
        {"orderId": f"r{index}", "date": purchased_at, "channel": "online", "items": [{
            "productId": "p-cat", "name": "Test cat food", "category": "pet-food",
            "quantity": 1, "unit": "piece", "price": 100,
        }]}
        for index, purchased_at in enumerate((
            "2026-08-01T10:00:00+03:00", "2026-08-15T10:00:00+03:00",
            "2026-08-29T10:00:00+03:00",
        ), start=1)
    ]
    purchases = normalize_purchase_history(raw).purchases
    suggestions = analyze_recurring(purchases, [Pet(species="cat", count=1)], date(2026, 9, 10))
    assert len(suggestions) == 1
    assert suggestions[0].product_id == "p-cat"
    assert suggestions[0].average_interval_days == 14


def test_async_adapter_marks_online_and_offline_channels():
    class FakeSession:
        async def call_tool(self, name, arguments):
            channel = "online" if "online" in name else "offline"
            payload = [{"orderId": channel, "date": "2026-09-01T10:00:00Z", "items": [{
                "productId": f"p-{channel}", "name": channel, "category": "test",
                "quantity": 1, "unit": "piece",
            }]}]
            return SimpleNamespace(content=[SimpleNamespace(text=json.dumps(payload))])

    result = asyncio.run(get_normalized_purchase_history(FakeSession()))
    assert [purchase["channel"] for purchase in result.purchases] == ["online", "offline"]
