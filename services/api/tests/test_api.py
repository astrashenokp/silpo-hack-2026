from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient

from conftest import create_plan
from smart_basket.app import create_app
from smart_basket.schemas import ProductCandidate, ProductSearchResponse, UserContext


def reference(plan):
    return {"runId": plan["runId"], "version": plan["version"]}


def owner(app, client):
    return app.state.sessions[client.cookies["smart_basket_demo"]]


def test_demo_plan_arithmetic_and_wire_format(client, planning_request):
    plan = create_plan(client, planning_request)
    assert plan["dataMode"] == "demo"
    assert len(plan["mealPlan"]) == 12
    assert plan["basketTotalMinor"] == 49000
    assert plan["budgetRemainingMinor"] == 131000
    assert plan["savingsMinor"] is None
    assert plan["effectiveRequest"] == planning_request
    assert plan["recurringItems"] == []
    ingredient_quantities = {
        item["id"]: item["quantity"]
        for item in plan["ingredients"]
    }

    assert ingredient_quantities == {
        "oats": 600,
        "rice": 1440,
        "lentils": 1200,
    }
    assert plan["mealPlan"][0]["ingredientAmounts"][0]["quantity"] == 150
    assert plan["mealPlan"][0]["calorieTarget"] == {
        "share": 0.25,
        "targetKcalPerServing": 500.0,
        "minKcalPerServing": 450.0,
        "maxKcalPerServing": 550.0,
    }
    assert plan["nutritionSummary"]["daily"][0] == {
        "day": 1,
        "targetKcalPerPerson": 2000.0,
        "plannedKcalPerPerson": 1860.0,
        "minKcalPerPerson": 1800.0,
        "maxKcalPerPerson": 2200.0,
        "withinTargetRange": True,
    }
    assert "Sofiia synthetic fallback" in " ".join(plan["warnings"])
    assert plan["canConfirmCart"] is True
    assert client.get("/api/health").headers["X-Data-Mode"] == "demo"


@pytest.mark.parametrize("field,value", [
    ("budgetMinor", 0), ("budgetMinor", 12.5), ("budgetMinor", "180000"),
    ("budgetMinor", True), ("days", 15), ("people", 0), ("days", True),
    ("currency", "USD"), ("restrictions", ["unrecognized"]),
    ("preferences", ["unsupported"]), ("includeRecurring", "true"),
    ("caloriesPerPersonPerDay", -1), ("healthConditions", ["unknown"]),
    ("cookingTimeLimit", 4), ("pets", [{"species": "cat", "count": 0}]),
    ("accountId", "user-supplied"),
])
def test_strict_request_validation(client, planning_request, field, value):
    response = client.post("/api/plans", json={**planning_request, field: value})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_null_calories_and_no_restrictions(client, planning_request):
    plan = create_plan(client, {**planning_request, "caloriesPerPersonPerDay": None})
    assert plan["effectiveRequest"]["caloriesPerPersonPerDay"] is None


@pytest.mark.parametrize("preferences,restrictions", [
    (["vegan"], []),
    (["paleo"], ["gluten-free"]),
    (["high-protein", "high-fiber"], ["soy-free", "dairy-free"]),
    ([], ["pork-free", "shellfish-free", "egg-free", "tree-nut-free"]),
])
def test_new_dietary_labels_accepted_by_api(client, planning_request, preferences, restrictions):
    body = {**planning_request, "preferences": preferences, "restrictions": restrictions}
    response = client.post("/api/plans", json=body)
    assert response.status_code == 202


def test_fourteen_day_request_is_accepted_by_api(client, planning_request):
    response = client.post("/api/plans", json={**planning_request, "days": 14})
    assert response.status_code == 202


def test_auth_and_session_isolation(app, client, planning_request):
    plan = create_plan(client, planning_request)
    cart = client.post("/api/cart/preview", json=reference(plan)).json()
    with TestClient(app) as stranger:
        assert stranger.get(f"/api/plans/{plan['runId']}").status_code == 401
        stranger.get("/api/context")
        assert stranger.get(f"/api/plans/{plan['runId']}").status_code == 404
        assert stranger.post("/api/cart/confirm", json={"previewId": cart["previewId"],
            "idempotencyKey": "other"}).status_code == 404
        stranger.cookies.set("smart_basket_demo", "invented-session")
        assert stranger.get(f"/api/plans/{plan['runId']}").status_code == 401


def test_planning_failure_and_over_budget(client, planning_request):
    response = client.post("/api/plans", json=planning_request, headers={"X-Demo-Scenario": "failed"})
    failed = client.get(f"/api/plans/{response.json()['runId']}").json()
    assert failed["status"] == "failed" and failed["result"] is None
    assert failed["error"]["code"] == "UPSTREAM_UNAVAILABLE"
    plan = create_plan(client, {**planning_request, "budgetMinor": 100})
    assert plan["budgetStatus"] == "over_budget"
    assert plan["budgetRemainingMinor"] == -48900
    assert not plan["canConfirmCart"]
    assert client.post("/api/cart/preview", json=reference(plan)).status_code == 409


@pytest.mark.parametrize("scenario,expected_total,status", [
    ("success", 52500, "success"), ("partial", 15500, "partial"), ("failed", 3500, "failed"),
])
def test_cart_outcomes_are_idempotent(app, client, planning_request, scenario, expected_total, status):
    plan = create_plan(client, planning_request)
    session = owner(app, client)
    assert session.cart == {"demo-existing-soap": (1.0, 3500)}
    preview = client.post("/api/cart/preview", json=reference(plan), headers={"X-Demo-Scenario": scenario}).json()
    assert preview["existingCartTotalMinor"] == 3500
    assert preview["addedGoodsTotalMinor"] == 49000
    assert preview["projectedGoodsTotalMinor"] == 52500
    body = {"previewId": preview["previewId"], "idempotencyKey": "once"}
    first = client.post("/api/cart/confirm", json=body)
    assert first.status_code == 200
    receipt = first.json()
    assert receipt["status"] == status
    assert receipt["verifiedCartTotalMinor"] == expected_total
    assert session.cart["demo-existing-soap"] == (1, 3500)
    assert client.post("/api/cart/confirm", json=body).json() == receipt
    assert client.post("/api/cart/confirm", json={**body, "idempotencyKey": "new-key"}).json() == receipt
    assert client.post("/api/cart/preview", json=reference(plan)).status_code == 409


def test_cart_adds_to_existing_product_and_serializes_confirm(app, client, planning_request):
    session = owner(app, client)
    session.cart["demo-oats"] = (3.0, 6000)
    plan = create_plan(client, planning_request)
    preview = client.post("/api/cart/preview", json=reference(plan)).json()
    assert preview["changes"][0]["beforeQuantity"] == 3
    assert preview["changes"][0]["afterQuantity"] == 5
    service = app.state.cart_service
    with ThreadPoolExecutor(max_workers=2) as pool:
        receipts = list(pool.map(lambda key: service.confirm_cart(preview["previewId"], key, session), ["a", "b"]))
    assert receipts[0] == receipts[1]
    assert session.cart["demo-oats"][0] == 5


@pytest.mark.parametrize("change", ["price", "availability", "cart", "expiry", "recalculate"])
def test_stale_cart_previews_block_changes(app, client, planning_request, change):
    plan = create_plan(client, planning_request)
    preview = client.post("/api/cart/preview", json=reference(plan)).json()
    session = owner(app, client)
    if change == "price":
        app.state.catalog.products["demo-oats"].price_minor += 1
    elif change == "availability":
        app.state.catalog.products["demo-oats"].available = False
    elif change == "cart":
        session.cart["demo-new-item"] = (1, 1000)
    elif change == "expiry":
        session.cart_previews[preview["previewId"]][0].expires_at = "2000-01-01T00:00:00+00:00"
    else:
        new = client.post(f"/api/plans/{plan['runId']}/recalculate", json={"version": 1, "selectedRecurringIds": []})
        new_plan = client.get(f"/api/plans/{new.json()['runId']}").json()["result"]
        assert new_plan["version"] == 2
        assert new_plan["effectiveRequest"] == planning_request
    before = dict(session.cart)
    response = client.post("/api/cart/confirm", json={"previewId": preview["previewId"], "idempotencyKey": "one"})
    assert response.status_code == 409, response.text
    assert session.cart == before


def test_recalculation_rejects_unknown_ids(client, planning_request):
    plan = create_plan(client, planning_request)
    assert client.post(f"/api/plans/{plan['runId']}/recalculate", json={"version": 1,
        "selectedRecurringIds": ["invented"]}).status_code == 400


def test_cors_errors_and_unimplemented_oauth(client, planning_request):
    response = client.options("/api/plans", headers={"Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type,x-demo-scenario"})
    assert response.headers["access-control-allow-credentials"] == "true"
    assert client.post("/api/plans", json=planning_request, headers={"Origin": "https://untrusted.test"}).status_code == 403
    assert client.get("/api/missing").json()["error"]["code"] == "NOT_FOUND"
    assert client.get("/api/integrations/fatsecret").json()["connected"] is False


def test_silpo_oauth_routes_use_server_session():
    class FakeSilpoOAuth:
        async def cancel(self, owner):
            self.cancelled_for = owner.id

        async def start(self, owner):
            self.started_for = owner.id
            return "https://auth.silpo.test/authorize?state=generated"

        async def finish(self, owner, *, code, state, iss):
            self.callback = {"code": code, "state": state, "iss": iss}
            with owner.lock:
                owner.silpo_connected = True
                owner.silpo_tools = ("silpo_get_my_profile",)

        def return_url(self, *, connected):
            assert connected is True
            return "http://localhost:3000?silpo=connected"

    oauth = FakeSilpoOAuth()
    app = create_app(silpo_oauth=oauth)
    with TestClient(app) as auth_client:
        auth_client.get("/api/context")
        started = auth_client.get("/api/auth/silpo/start", follow_redirects=False)
        assert started.status_code == 302
        assert started.headers["location"].startswith("https://auth.silpo.test/authorize")

        callback = auth_client.get(
            "/api/auth/silpo/callback?code=one&state=generated&iss=https://auth.silpo.test",
            follow_redirects=False,
        )
        assert callback.status_code == 303
        assert callback.headers["location"] == "http://localhost:3000?silpo=connected"
        assert oauth.callback == {
            "code": "one",
            "state": "generated",
            "iss": "https://auth.silpo.test",
        }
        assert auth_client.get("/api/integrations/silpo").json() == {
            "connected": True,
            "toolsAvailable": ["silpo_get_my_profile"],
            "reason": None,
        }


def test_silpo_callback_requires_code_and_state(client):
    class FakeSilpoOAuth:
        async def cancel(self, owner):
            self.cancelled_for = owner.id

    oauth = FakeSilpoOAuth()
    app = create_app(silpo_oauth=oauth)
    with TestClient(app) as auth_client:
        auth_client.get("/api/context")
        response = auth_client.get("/api/auth/silpo/callback?code=one")
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "INVALID_OAUTH_CALLBACK"
        assert oauth.cancelled_for


def test_context_uses_silpo_after_connection(app, client, monkeypatch):
    session = owner(app, client)
    session.silpo_connected = True

    @asynccontextmanager
    async def fake_mcp_session(storage):
        yield object()

    async def fake_user_context(mcp_session, session_owner):
        assert session_owner is session
        return UserContext(
            preferences=["vegetarian"], restrictions=[], pets=[],
            history_available=True, cart_context_ready=True, warnings=[],
        )

    monkeypatch.setattr("smart_basket.routes.api.get_mcp_session", fake_mcp_session)
    monkeypatch.setattr("smart_basket.routes.api.get_user_context", fake_user_context)
    response = client.get("/api/context")
    assert response.status_code == 200
    assert response.headers["X-Data-Mode"] == "live"
    assert response.json()["historyAvailable"] is True


def test_product_search_uses_stored_branch(app, client, monkeypatch):
    session = owner(app, client)
    session.silpo_connected = True
    session.silpo_branch_id = "stored-branch"
    session.silpo_cart_id = "stored-cart"
    session.silpo_delivery_type = "SelfPickup"
    session.silpo_timeslot = {"start": "start", "end": "end"}
    session.silpo_tool_schemas["silpo_find_products_batch"] = {
        "type": "object",
        "properties": {"items": {"type": "array", "items": {"type": "string"}}},
        "required": ["items"],
    }

    @asynccontextmanager
    async def fake_mcp_session(storage):
        yield object()

    async def fake_search(
        mcp_session, query, branch_id, *, cart_id, delivery_type, timeslot, tool_schemas,
    ):
        assert branch_id == "stored-branch"
        assert cart_id == "stored-cart"
        assert delivery_type == "SelfPickup"
        assert timeslot == {"start": "start", "end": "end"}
        assert "silpo_find_products_batch" in tool_schemas
        return ProductSearchResponse(query=query, products=[ProductCandidate(
            id="p1", name="Rice", requirement_ids=[], price_minor=8000,
            selling_unit="package", quantity_step=1.0, content_quantity=1000.0,
            content_unit="g", available=True, restriction_check="unknown",
            regular_price_minor=None, source="silpo", checked_at="2026-09-10T12:00:00+00:00",
        )], warnings=[])

    monkeypatch.setattr("smart_basket.routes.api.get_mcp_session", fake_mcp_session)
    monkeypatch.setattr("smart_basket.routes.api.search_products", fake_search)
    response = client.get("/api/integrations/silpo/products?query=rice")
    assert response.status_code == 200
    assert response.headers["X-Data-Mode"] == "live"
    assert response.json()["products"][0]["priceMinor"] == 8000


def test_product_search_requires_cart_context(app, client):
    session = owner(app, client)
    session.silpo_connected = True
    response = client.get("/api/integrations/silpo/products?query=rice")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CART_CONTEXT_REQUIRED"


def test_live_mode_fails_closed(monkeypatch):
    monkeypatch.setenv("SMART_BASKET_MODE", "live")
    with pytest.raises(RuntimeError, match="Only demo"):
        create_app()


def test_injected_planner_failure_does_not_expose_details(app, client, planning_request):
    class FailingPlanner:
        def run_planner(self, *args):
            raise RuntimeError("private upstream details")
    app.state.planner = FailingPlanner()
    queued = client.post("/api/plans", json=planning_request).json()
    run = client.get(f"/api/plans/{queued['runId']}").json()
    assert run["status"] == "failed"
    assert "private" not in str(run)


def test_filters_endpoint_returns_all_supported_labels(client):
    response = client.get("/api/filters")
    assert response.status_code == 200
    body = response.json()
    assert set(body["preferences"]) == {"vegetarian", "vegan", "paleo", "high-protein", "high-fiber"}
    assert set(body["restrictions"]) == {
        "peanut-free", "gluten-free", "dairy-free", "tree-nut-free",
        "shellfish-free", "soy-free", "egg-free", "pork-free",
    }
