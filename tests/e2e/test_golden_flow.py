"""Golden demo path over the public HTTP surface (docs/PRODUCT.md#golden-demo-input)."""

import pytest

from stack import completed_result, line_total, plan_ref, poll_export, start_plan

RESULT_FIELDS = {
    "runId", "version", "dataMode", "effectiveRequest", "mealPlan", "nutritionSummary",
    "ingredients", "recurringItems", "selectedProducts", "substitutions", "budgetMinor",
    "basketTotalMinor", "budgetRemainingMinor", "savingsMinor", "budgetStatus",
    "unresolvedRequirements", "warnings", "canConfirmCart",
}
SLOTS = ("breakfast", "lunch", "dinner")
STAGES = {"context", "history", "meals", "matching", "optimization", "ready"}


def test_health_reports_demo_mode(anonymous):
    response = anonymous.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mode": "demo"}
    assert response.headers["x-data-mode"] == "demo"


def test_filters_expose_supported_labels(anonymous):
    response = anonymous.get("/api/filters")
    assert response.status_code == 200, response.text
    labels = response.json()
    assert "vegetarian" in labels["preferences"]
    assert "peanut-free" in labels["restrictions"]


def test_context_issues_session_cookie(anonymous):
    response = anonymous.get("/api/context")
    assert response.status_code == 200, response.text
    assert "smart_basket_demo" in anonymous.cookies
    assert {"preferences", "restrictions", "pets", "historyAvailable",
            "cartContextReady", "warnings"} <= set(response.json())


def test_progress_reports_completed_stages(client, planning_request):
    run = start_plan(client, planning_request)
    assert run["status"] == "completed", run
    assert run["stage"] == "ready"
    stages = [event["stage"] for event in run["events"]]
    assert stages and set(stages) <= STAGES
    assert stages[-1] == "ready"


def test_golden_plan_follows_contract(client, planning_request):
    result = completed_result(client, planning_request)

    assert set(result) == RESULT_FIELDS
    assert result["version"] == 1
    assert result["dataMode"] in {"demo", "mixed"}
    assert result["effectiveRequest"] == planning_request

    days = range(1, planning_request["days"] + 1)
    assert {(m["day"], m["slot"]) for m in result["mealPlan"]} == {(d, s) for d in days for s in SLOTS}
    assert all(m["servings"] == planning_request["people"] for m in result["mealPlan"])

    products = result["selectedProducts"]
    assert products, "the golden plan should propose products"
    for product in products:
        assert isinstance(product["unitPriceMinor"], int)
        assert product["lineTotalMinor"] == line_total(product["quantity"], product["unitPriceMinor"])
        if result["dataMode"] == "demo":
            assert product["source"] == "synthetic", "demo results must not claim live Silpo products"
    assert result["basketTotalMinor"] == sum(p["lineTotalMinor"] for p in products)
    assert result["budgetMinor"] == planning_request["budgetMinor"]
    assert result["budgetRemainingMinor"] == result["budgetMinor"] - result["basketTotalMinor"]
    assert not any(item["selected"] for item in result["recurringItems"])


def test_golden_plan_matches_documented_demo_numbers(client, planning_request):
    """fixtures/README.md: 600 g oats, 1440 g rice, 1200 g lentils -> 49000 kopiykas."""
    result = completed_result(client, planning_request)
    demand = {i["id"]: (i["quantity"], i["unit"]) for i in result["ingredients"]}
    assert demand == {"oats": (600, "g"), "rice": (1440, "g"), "lentils": (1200, "g")}
    assert result["basketTotalMinor"] == 49000
    assert result["budgetRemainingMinor"] == 131000
    assert result["budgetStatus"] == "within_budget"
    assert result["canConfirmCart"] is True


def test_meal_amounts_add_up_to_shopping_list(client, planning_request):
    result = completed_result(client, planning_request)
    per_meal = {}
    for meal in result["mealPlan"]:
        for amount in meal["ingredientAmounts"]:
            key = (amount["ingredientId"], amount["unit"])
            per_meal[key] = per_meal.get(key, 0) + amount["quantity"]
    aggregate = {(i["id"], i["unit"]): i["quantity"] for i in result["ingredients"]}
    assert per_meal.keys() == aggregate.keys()
    assert per_meal == pytest.approx(aggregate)


def test_calorie_target_uses_documented_split(client, planning_request):
    summary = completed_result(client, planning_request)["nutritionSummary"]
    assert summary["calorieTargetKcalPerPersonPerDay"] == planning_request["caloriesPerPersonPerDay"]
    shares = {entry["slot"]: entry["share"] for entry in summary["distribution"]}
    total = sum(shares.values())
    assert {slot: share / total for slot, share in shares.items()} == pytest.approx(
        {"breakfast": 0.25, "lunch": 0.35, "dinner": 0.40})
    assert [day["day"] for day in summary["daily"]] == list(range(1, planning_request["days"] + 1))


def test_cart_preview_and_confirmation_are_idempotent(client, planning_request):
    result = completed_result(client, planning_request)
    response = client.post("/api/cart/preview", json=plan_ref(result))
    assert response.status_code == 200, response.text
    preview = response.json()
    assert (preview["runId"], preview["version"]) == (result["runId"], result["version"])
    assert preview["addedGoodsTotalMinor"] == result["basketTotalMinor"]
    assert preview["projectedGoodsTotalMinor"] == (
        preview["existingCartTotalMinor"] + preview["addedGoodsTotalMinor"])
    additions = {c["productId"]: c["afterQuantity"] - c["beforeQuantity"] for c in preview["changes"]}
    assert additions == {p["productId"]: p["quantity"] for p in result["selectedProducts"]}

    confirmation = {"previewId": preview["previewId"], "idempotencyKey": "e2e-golden-cart"}
    first = client.post("/api/cart/confirm", json=confirmation)
    assert first.status_code == 200, first.text
    receipt = first.json()
    assert receipt["status"] == "success", receipt
    assert {item["productId"] for item in receipt["items"]} == set(additions)
    assert all(item["status"] == "success" for item in receipt["items"])
    assert receipt["verifiedCartTotalMinor"] == preview["projectedGoodsTotalMinor"]

    # A double click or retry with the same key must return the same outcome, not add twice.
    again = client.post("/api/cart/confirm", json=confirmation)
    assert again.status_code == 200, again.text
    assert again.json() == receipt


def test_fatsecret_saves_one_personal_portion(client, planning_request):
    result = completed_result(client, planning_request)
    status = client.get("/api/integrations/fatsecret").json()
    assert status["connected"] is False
    assert status["accountLabel"] is None
    assert "DEMO" in status["reason"]

    meal = next(m for m in result["mealPlan"] if m["slot"] == "lunch")
    response = client.post("/api/fatsecret/exports/preview",
                           json={**plan_ref(result), "mealIds": [meal["id"]]})
    assert response.status_code == 200, response.text
    preview = response.json()
    assert preview["destination"] == "saved_meals"
    assert preview["portionBasis"] == "one_person"
    assert preview["canConfirm"] is True
    [exported] = preview["meals"]
    assert exported["mealId"] == meal["id"] and exported["unresolved"] == []
    per_meal = {a["ingredientId"]: a["quantity"] for a in meal["ingredientAmounts"]}
    assert {item["ingredientId"] for item in exported["items"]} == set(per_meal)
    for item in exported["items"]:
        assert item["sourceQuantity"] == pytest.approx(per_meal[item["ingredientId"]] / meal["servings"])

    confirmation = {"previewId": preview["previewId"], "idempotencyKey": "e2e-golden-export"}
    accepted = client.post("/api/fatsecret/exports/confirm", json=confirmation)
    assert accepted.status_code == 202, accepted.text
    export_id = accepted.json()["exportId"]
    export = poll_export(client, export_id)
    assert export["status"] == "success", export
    assert [m["status"] for m in export["meals"]] == ["saved"]

    repeat = client.post("/api/fatsecret/exports/confirm", json=confirmation)
    assert repeat.status_code == 202, repeat.text
    assert repeat.json()["exportId"] == export_id
