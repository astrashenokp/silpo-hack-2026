from contextlib import asynccontextmanager

import pytest

from conftest import create_plan
from smart_basket.catalog.live import SessionCatalog, _run_async
from smart_basket.cart.service import normalize_cart_snapshot, snapshot_total
from smart_basket.core import Session
from smart_basket.schemas import ProductCandidate, ProductSearchResponse


def _owner(app, client):
    return app.state.sessions[client.cookies["smart_basket_demo"]]


@pytest.mark.asyncio
async def test_sync_planner_bridge_runs_from_anyio_worker():
    import anyio

    async def value():
        return "live"

    result = await anyio.to_thread.run_sync(lambda: _run_async(value))
    assert result == "live"


def test_cart_snapshot_tracks_unpriced_lines_for_stale_detection():
    snapshot = normalize_cart_snapshot({"products": [
        {"productId": "priced", "quantity": 2, "priceMinor": 100},
        {"productId": "unpriced", "quantity": 1},
    ]})
    assert snapshot == {"priced": (2.0, 100), "unpriced": (1.0, None)}
    assert snapshot_total(snapshot) == 200


@pytest.mark.asyncio
async def test_live_catalog_uses_localized_aliases_and_passes_owner(monkeypatch):
    owner = Session("owner")
    owner.silpo_connected = True
    owner.silpo_branch_id = "branch-1"
    queries = []

    @asynccontextmanager
    async def fake_session(storage):
        yield object()

    async def fake_search(_session, query, branch_id, **kwargs):
        queries.append(query)
        assert branch_id == "branch-1"
        assert kwargs["owner"] is owner
        product = ProductCandidate(
            id=f"product-{len(queries)}", name=query, requirement_ids=[],
            price_minor=100, selling_unit="package", quantity_step=1.0,
            content_quantity=500.0, content_unit="g", available=True,
            restriction_check="unknown", regular_price_minor=None,
            source="silpo", checked_at="2026-09-11T00:00:00+00:00",
        )
        return ProductSearchResponse(query=query, products=[product], warnings=[])

    monkeypatch.setattr("smart_basket.catalog.live.get_mcp_session", fake_session)
    monkeypatch.setattr("smart_basket.catalog.live.search_products", fake_search)
    products = await SessionCatalog()._search(owner, "rice")

    assert queries == ["крупа рисова", "рис", "rice"]
    assert len(products) == 3
    assert all(product.restriction_check == "pass" for product in products)


def _make_plan_live(app, client, planning_request):
    wire_plan = create_plan(client, planning_request)
    owner = _owner(app, client)
    plan = owner.runs[wire_plan["runId"]].result
    owner.silpo_connected = True
    owner.silpo_cart_id = "cart-1"
    owner.silpo_branch_id = "branch-1"
    owner.silpo_delivery_type = "SelfPickup"
    owner.silpo_timeslot = {"start": "start", "end": "end"}
    owner.silpo_tool_schemas["silpo_add_or_update_cart_products"] = {
        "type": "object",
        "properties": {
            "products": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "productId": {"type": "string"},
                        "companyId": {"type": "string"},
                        "branchId": {"type": "string"},
                        "quantity": {"type": "number"},
                    },
                    "required": ["productId", "companyId", "branchId", "quantity"],
                },
            },
            "shoppingCartId": {"type": "string"},
        },
        "required": ["products", "shoppingCartId"],
    }
    for index, selected in enumerate(plan.selected_products):
        selected.product_id = f"live-{index}"
        selected.source = "silpo"
        owner.silpo_product_write_metadata[selected.product_id] = {
            "productId": selected.product_id,
            "companyId": f"company-{index}",
            "branchId": "branch-1",
        }
    plan.data_mode = "mixed"
    plan.can_confirm_cart = True
    return wire_plan, owner, plan


@pytest.mark.asyncio
async def test_live_cart_preview_confirm_readback_and_idempotency(
    app, client, planning_request, monkeypatch
):
    wire_plan, owner, plan = _make_plan_live(app, client, planning_request)
    state = {"written": False, "calls": []}

    @asynccontextmanager
    async def fake_session(storage):
        yield object()

    async def fake_cart(_session):
        items = [{"productId": "unrelated", "quantity": 1, "priceMinor": 3000}]
        if state["written"]:
            items.extend({
                "productId": selected.product_id,
                "quantity": selected.quantity,
                "priceMinor": selected.unit_price_minor,
            } for selected in plan.selected_products)
        return {"shoppingCartId": "cart-1", "products": items}

    async def fake_details(_session, product_id, branch_id):
        selected = next(item for item in plan.selected_products if item.product_id == product_id)
        assert branch_id == "branch-1"
        return {"product": {
            "productId": selected.product_id,
            "title": selected.name,
            "currentPriceMinor": selected.unit_price_minor,
            "sellingUnit": selected.selling_unit,
            "quantityStep": 1,
            "available": True,
        }}

    async def fake_write(_session, products, **context):
        state["calls"].append((products, context))
        state["written"] = True
        return {"success": True}

    monkeypatch.setattr("smart_basket.cart.service.get_mcp_session", fake_session)
    monkeypatch.setattr("smart_basket.cart.service.get_current_cart", fake_cart)
    monkeypatch.setattr("smart_basket.cart.service.get_product_details", fake_details)
    monkeypatch.setattr("smart_basket.cart.service.add_or_update_cart_products", fake_write)

    preview_response = client.post("/api/cart/preview", json={
        "runId": wire_plan["runId"], "version": wire_plan["version"],
    })
    assert preview_response.status_code == 200, preview_response.text
    preview = preview_response.json()
    assert preview["existingCartTotalMinor"] == 3000
    assert preview["projectedGoodsTotalMinor"] == 3000 + plan.basket_total_minor
    assert all(change["beforeQuantity"] == 0 for change in preview["changes"])

    body = {"previewId": preview["previewId"], "idempotencyKey": "live-once"}
    first = client.post("/api/cart/confirm", json=body)
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "success"
    assert len(state["calls"]) == 1
    products, context = state["calls"][0]
    assert {item["productId"] for item in products} == {
        item.product_id for item in plan.selected_products
    }
    assert "unrelated" not in {item["productId"] for item in products}
    assert context["cart_id"] == "cart-1"

    repeated = client.post("/api/cart/confirm", json=body)
    assert repeated.json() == first.json()
    assert len(state["calls"]) == 1
    assert wire_plan["runId"] in owner.live_cart_applied_runs


@pytest.mark.asyncio
async def test_live_cart_uncertain_write_uses_readback(
    app, client, planning_request, monkeypatch
):
    wire_plan, _owner_session, plan = _make_plan_live(app, client, planning_request)
    reads = 0

    @asynccontextmanager
    async def fake_session(storage):
        yield object()

    async def fake_cart(_session):
        nonlocal reads
        reads += 1
        products = [] if reads < 3 else [{
            "productId": item.product_id,
            "quantity": item.quantity,
            "priceMinor": item.unit_price_minor,
        } for item in plan.selected_products]
        return {"shoppingCartId": "cart-1", "products": products}

    async def fake_details(_session, product_id, _branch_id):
        selected = next(item for item in plan.selected_products if item.product_id == product_id)
        return {"product": {
            "productId": selected.product_id,
            "title": selected.name,
            "currentPriceMinor": selected.unit_price_minor,
            "sellingUnit": selected.selling_unit,
            "quantityStep": 1,
            "available": True,
        }}

    async def uncertain_write(*args, **kwargs):
        raise TimeoutError("provider response timed out")

    monkeypatch.setattr("smart_basket.cart.service.get_mcp_session", fake_session)
    monkeypatch.setattr("smart_basket.cart.service.get_current_cart", fake_cart)
    monkeypatch.setattr("smart_basket.cart.service.get_product_details", fake_details)
    monkeypatch.setattr("smart_basket.cart.service.add_or_update_cart_products", uncertain_write)

    preview = client.post("/api/cart/preview", json={
        "runId": wire_plan["runId"], "version": wire_plan["version"],
    }).json()
    receipt = client.post("/api/cart/confirm", json={
        "previewId": preview["previewId"], "idempotencyKey": "uncertain",
    })
    assert receipt.status_code == 200, receipt.text
    assert receipt.json()["status"] == "success"
    assert "uncertain" in " ".join(receipt.json()["warnings"]).lower()
