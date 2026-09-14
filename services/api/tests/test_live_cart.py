from contextlib import asynccontextmanager

import pytest

from conftest import create_plan
from smart_basket.catalog.live import (
    SessionCatalog,
    _field_paths,
    _package_signals,
    _run_async,
    ingredient_package_amount,
    live_query_profile,
    live_product_name_matches,
    restriction_check_from_details,
)
from smart_basket.catalog.matching import MatchingContext, find_product_candidates
from smart_basket.cart.service import normalize_cart_snapshot, snapshot_total
from smart_basket.core import Session
from smart_basket.schemas import (
    IngredientRequirement, ProductCandidate, ProductSearchResponse, UserContext,
)


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


def test_detail_field_paths_do_not_include_values():
    paths = _field_paths({"product": {
        "attributes": [{"name": "Склад", "value": "секретне значення"}],
    }})
    assert "product.attributes[].value" in paths
    assert all("секретне значення" not in path for path in paths)


def test_package_signals_extract_catalog_quantity_fields():
    assert _package_signals({"product": {
        "weighted": False,
        "step": 1,
        "ratio": 0.5,
        "displayRatio": "500 г",
        "attributes": {"Розмір/об'єм": "0,5 кг", "Продавець": "Silpo"},
    }}) == {
        "weighted": False,
        "step": 1,
        "ratio": 0.5,
        "displayRatio": "500 г",
        "attributes.Розмір/об'єм": "0,5 кг",
    }


@pytest.mark.parametrize(("payload", "expected"), [
    ({"healthLabels": ["FISH_FREE", "RED_MEAT_FREE"]}, "pass"),
    ({"composition": "рисова крупа, вода, сіль"}, "pass"),
    ({"characteristics": [{"name": "Склад", "value": "рисова крупа"}]}, "pass"),
    ({"attributes": [{"propertyName": "Склад продукту", "propertyValue": "рис, тунець"}]}, "fail"),
    ({"ingredients": "рис, тунець, сіль"}, "fail"),
    ({"description": "звичайний рис"}, "unknown"),
    ({}, "unknown"),
])
def test_live_restriction_check_requires_provider_evidence(payload, expected):
    assert restriction_check_from_details(
        payload, ["fish-free", "red-meat-free"]
    ) == expected


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
            content_quantity=None, content_unit=None, available=True,
            restriction_check="unknown", regular_price_minor=None,
            source="silpo", checked_at="2026-09-11T00:00:00+00:00",
        )
        owner.silpo_product_write_metadata[product.id] = {
            "productId": product.id,
            "companyId": "company-from-search",
            "branchId": branch_id,
            "slug": f"slug-{len(queries)}",
        }
        return ProductSearchResponse(query=query, products=[product], warnings=[])

    async def fake_details(_session, product_id, branch_id, **kwargs):
        assert branch_id == "branch-1"
        assert kwargs["slug"].startswith("slug-")
        assert kwargs["delivery_type"] is None
        assert kwargs["input_schema"] is None
        return {
            "productId": product_id,
            "branchId": branch_id,
            "packageSize": "500 г",
            "composition": "рисова крупа",
        }

    monkeypatch.setattr("smart_basket.catalog.live.get_mcp_session", fake_session)
    monkeypatch.setattr("smart_basket.catalog.live.search_products", fake_search)
    monkeypatch.setattr("smart_basket.catalog.live.get_silpo_product_details", fake_details)
    products = await SessionCatalog()._search(owner, "rice")

    assert queries == ["крупа рисова", "рис"]
    assert len(products) == 2
    assert all(product.restriction_check == "unknown" for product in products)
    assert all(product.content_quantity == 500 for product in products)
    assert all(product.content_unit == "g" for product in products)
    assert all(
        metadata["companyId"] == "company-from-search"
        for metadata in owner.silpo_product_write_metadata.values()
    )


@pytest.mark.asyncio
async def test_connected_catalog_without_cart_branch_does_not_mix_demo_candidates():
    owner = Session("owner")
    owner.silpo_connected = True

    products = await SessionCatalog()._search(owner, "rice")

    assert products == []


def test_connected_matching_without_live_context_stays_unresolved():
    owner = Session("owner")
    owner.silpo_connected = True
    catalog = SessionCatalog()
    requirement = IngredientRequirement(
        id="rice", name="Dry rice", search_terms=["rice"], quantity=500.0,
        unit="g", meal_ids=["meal-1"], restrictions=["fish-free"],
    )

    result = find_product_candidates(
        [requirement], [], MatchingContext(owner, catalog, catalog.check_restrictions),
    )

    assert result.unresolved_requirements
    assert result.candidates == []


def test_connected_catalog_reuses_context_and_history_loaded_for_the_form():
    owner = Session("owner")
    owner.silpo_connected = True
    owner.silpo_context = UserContext(
        preferences=["vegetarian"], restrictions=["fish-free"],
        pets=[{"species": "dog", "count": 1}], history_available=False,
        cart_context_ready=False, warnings=["Silpo purchase history is empty."],
    )
    owner.silpo_purchase_history = []
    catalog = SessionCatalog()

    context = catalog.get_user_context(owner)
    history = catalog.get_purchase_history(owner)

    assert context.preferences == ["vegetarian"]
    assert context.pets[0].species == "dog"
    assert history == []
    assert context is not owner.silpo_context


def test_live_history_failure_uses_empty_demo_fallback(monkeypatch):
    owner = Session("owner")
    owner.silpo_connected = True
    catalog = SessionCatalog()

    async def failed_history(_owner):
        raise RuntimeError("temporary MCP failure")

    monkeypatch.setattr(catalog, "_history", failed_history)

    assert catalog.get_purchase_history(owner) == []


@pytest.mark.asyncio
async def test_live_search_failure_does_not_mix_demo_candidates(monkeypatch):
    owner = Session("owner")
    owner.silpo_connected = True
    owner.silpo_branch_id = "branch-1"
    catalog = SessionCatalog()

    async def failed_search(_owner, _query):
        raise RuntimeError("temporary MCP failure")

    monkeypatch.setattr(catalog, "_search_live", failed_search)

    products = await catalog._search(owner, "rice")

    assert products == []


@pytest.mark.asyncio
async def test_empty_live_search_does_not_mix_demo_candidates(monkeypatch):
    owner = Session("owner")
    owner.silpo_connected = True
    owner.silpo_branch_id = "branch-1"

    @asynccontextmanager
    async def fake_session(storage):
        yield object()

    async def empty_search(*args, **kwargs):
        return ProductSearchResponse(query="rice", products=[], warnings=[])

    monkeypatch.setattr("smart_basket.catalog.live.get_mcp_session", fake_session)
    monkeypatch.setattr("smart_basket.catalog.live.search_products", empty_search)

    products = await SessionCatalog()._search(owner, "rice")

    assert products == []


@pytest.mark.parametrize(("query", "product_name"), [
    ("all purpose flour", "Tanqueray Flor de Sevilla Gin"),
    ("tomato", "Пиво Underwood Red Tomato"),
    ("salt", "Льодяник Fizi Vanilla salt"),
    ("milk", "Цукерки-соломинки Quick Milk"),
])
def test_live_name_evidence_rejects_observed_fuzzy_false_positives(query, product_name):
    assert not live_product_name_matches(query, product_name)


@pytest.mark.parametrize(("query", "product_name"), [
    ("all purpose flour", "Борошно пшеничне Зерновита 1 кг"),
    ("tomato", "Помідор рожевий ваговий"),
    ("salt", "Сіль кухонна кам'яна 1 кг"),
    ("milk", "Молоко Селянське 2,5% 900 г"),
    ("onion", "Цибуля ріпчаста вагова"),
    ("extra virgin olive oil", "Олія оливкова Extra Virgin 500 мл"),
])
def test_live_name_evidence_accepts_relevant_silpo_products(query, product_name):
    assert live_product_name_matches(query, product_name)


@pytest.mark.parametrize(("query", "millilitres", "expected_grams"), [
    ("extra virgin olive oil", 500.0, 455.0),
    ("milk", 900.0, 927.0),
    ("white wine", 750.0, 742.5),
    ("water", 1000.0, 1000.0),
])
def test_known_liquid_packages_convert_to_edamam_grams(query, millilitres, expected_grams):
    assert ingredient_package_amount(
        live_query_profile(query), millilitres, "ml"
    ) == (expected_grams, "g")


@pytest.mark.asyncio
async def test_live_catalog_does_not_search_generic_edamam_category(monkeypatch):
    owner = Session("owner")
    owner.silpo_connected = True
    owner.silpo_branch_id = "branch-1"

    async def should_not_search(*args, **kwargs):
        raise AssertionError("generic category must not reach Silpo search")

    catalog = SessionCatalog()
    monkeypatch.setattr(catalog, "_search_live", should_not_search)

    assert await catalog._search(owner, "grains") == []


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

    async def fake_details(_session, product_id, branch_id, **_kwargs):
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
async def test_live_cart_preview_refreshes_missing_context_and_write_coordinates(
    app, client, planning_request, monkeypatch
):
    wire_plan, owner, plan = _make_plan_live(app, client, planning_request)
    owner.silpo_cart_id = None
    owner.silpo_branch_id = None
    owner.silpo_delivery_type = None
    owner.silpo_timeslot = None
    owner.silpo_product_write_metadata.clear()

    @asynccontextmanager
    async def fake_session(_storage):
        yield object()

    async def fake_context(_session, session_owner):
        session_owner.silpo_cart_id = "cart-refreshed"
        session_owner.silpo_branch_id = "branch-refreshed"
        session_owner.silpo_delivery_type = "SelfPickup"
        session_owner.silpo_timeslot = {"start": "start", "end": "end"}
        return UserContext(
            preferences=[], restrictions=[], pets=[], history_available=False,
            cart_context_ready=True, warnings=[],
        )

    async def fake_cart(_session):
        return {"shoppingCartId": "cart-refreshed", "products": []}

    async def fake_search(_session, query, branch_id, **kwargs):
        selected = next(item for item in plan.selected_products if item.name == query)
        assert branch_id == "branch-refreshed"
        assert kwargs["cart_id"] == "cart-refreshed"
        assert kwargs["owner"] is owner
        owner.silpo_product_write_metadata[selected.product_id] = {
            "productId": selected.product_id,
            "companyId": f"company-{selected.product_id}",
            "branchId": branch_id,
        }
        product = ProductCandidate(
            id=selected.product_id,
            name=selected.name,
            requirement_ids=list(selected.requirement_ids),
            price_minor=selected.unit_price_minor,
            selling_unit=selected.selling_unit,
            quantity_step=1.0,
            content_quantity=None,
            content_unit=None,
            available=True,
            restriction_check="pass",
            regular_price_minor=None,
            source="silpo",
            checked_at="2026-09-13T00:00:00+00:00",
        )
        return ProductSearchResponse(query=query, products=[product], warnings=[])

    monkeypatch.setattr("smart_basket.cart.service.get_mcp_session", fake_session)
    monkeypatch.setattr("smart_basket.cart.service.get_user_context", fake_context)
    monkeypatch.setattr("smart_basket.cart.service.get_current_cart", fake_cart)
    monkeypatch.setattr("smart_basket.cart.service.search_products", fake_search)

    response = client.post("/api/cart/preview", json={
        "runId": wire_plan["runId"], "version": wire_plan["version"],
    })

    assert response.status_code == 200, response.text
    assert len(response.json()["changes"]) == len(plan.selected_products)
    assert owner.silpo_cart_id == "cart-refreshed"
    assert all(
        owner.silpo_product_write_metadata[item.product_id].get("companyId")
        for item in plan.selected_products
    )


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

    async def fake_details(_session, product_id, _branch_id, **_kwargs):
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
