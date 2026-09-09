from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from conftest import create_plan
from smart_basket.app import create_app


def reference(plan):
    return {"runId": plan["runId"], "version": plan["version"]}


def owner(app, client):
    return app.state.sessions[client.cookies["smart_basket_demo"]]


def test_demo_plan_arithmetic_and_wire_format(client, planning_request):
    plan = create_plan(client, planning_request)
    assert plan["dataMode"] == "demo"
    assert len(plan["mealPlan"]) == 12
    assert plan["basketTotalMinor"] == 34000
    assert plan["budgetRemainingMinor"] == 146000
    assert plan["savingsMinor"] is None
    assert plan["effectiveRequest"] == planning_request
    assert plan["recurringItems"] == []
    ingredient_quantities = {
        item["id"]: item["quantity"]
        for item in plan["ingredients"]
    }

    assert ingredient_quantities == {
        "oats": 600,
        "rice": 960,
        "lentils": 840,
    }
    assert plan["mealPlan"][0]["ingredientAmounts"][0]["quantity"] == 150
    assert plan["canConfirmCart"] is True
    assert client.get("/api/health").headers["X-Data-Mode"] == "demo"


@pytest.mark.parametrize("field,value", [
    ("budgetMinor", 0), ("budgetMinor", 12.5), ("budgetMinor", "180000"),
    ("budgetMinor", True), ("days", 8), ("people", 0), ("days", True),
    ("currency", "USD"), ("restrictions", ["unrecognized"]),
    ("preferences", ["unsupported"]), ("includeRecurring", "true"),
    ("caloriesPerPersonPerDay", -1), ("pets", [{"species": "cat", "count": 0}]),
    ("accountId", "user-supplied"),
])
def test_strict_request_validation(client, planning_request, field, value):
    response = client.post("/api/plans", json={**planning_request, field: value})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_null_calories_and_no_restrictions(client, planning_request):
    plan = create_plan(client, {**planning_request, "caloriesPerPersonPerDay": None})
    assert plan["effectiveRequest"]["caloriesPerPersonPerDay"] is None


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
    assert plan["budgetRemainingMinor"] == -33900
    assert not plan["canConfirmCart"]
    assert client.post("/api/cart/preview", json=reference(plan)).status_code == 409


@pytest.mark.parametrize("scenario,expected_total,status", [
    ("success", 37500, "success"), ("partial", 15500, "partial"), ("failed", 3500, "failed"),
])
def test_cart_outcomes_are_idempotent(app, client, planning_request, scenario, expected_total, status):
    plan = create_plan(client, planning_request)
    session = owner(app, client)
    assert session.cart == {"demo-existing-soap": (1.0, 3500)}
    preview = client.post("/api/cart/preview", json=reference(plan), headers={"X-Demo-Scenario": scenario}).json()
    assert preview["existingCartTotalMinor"] == 3500
    assert preview["addedGoodsTotalMinor"] == 34000
    assert preview["projectedGoodsTotalMinor"] == 37500
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
    assert client.get("/api/auth/silpo/start").status_code == 503
    assert client.get("/api/integrations/fatsecret").json()["connected"] is False


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
