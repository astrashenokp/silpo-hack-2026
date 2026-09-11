"""Failure and safety scenarios from docs/QA_DEMO.md, exercised over HTTP."""

import pytest

from stack import (
    assert_error, completed_result, new_client, plan_ref, poll_export, poll_run, start_plan,
    start_session,
)


def recalculate(client, result, selected=()):
    return client.post(f"/api/plans/{result['runId']}/recalculate",
                       json={"version": result["version"], "selectedRecurringIds": list(selected)})


def test_requests_without_session_are_rejected(anonymous, planning_request):
    assert_error(anonymous.post("/api/plans", json=planning_request), 401, "AUTH_REQUIRED")
    assert_error(anonymous.get("/api/plans/demo-run-unknown"), 401, "AUTH_REQUIRED")


@pytest.mark.parametrize(("field", "value"), [
    ("days", 15), ("days", 0), ("people", 7), ("budgetMinor", 0), ("currency", "USD"),
    ("restrictions", ["not-a-supported-label"]), ("cookingTimeLimit", 3),
])
def test_invalid_requests_are_rejected(client, planning_request, field, value):
    response = client.post("/api/plans", json={**planning_request, field: value})
    assert_error(response, 400, "VALIDATION_ERROR")


def test_unknown_demo_scenario_is_rejected(client, planning_request):
    response = client.post("/api/plans", json=planning_request, headers={"X-Demo-Scenario": "chaos"})
    assert_error(response, 400, "VALIDATION_ERROR")


def test_unknown_run_is_not_found(client):
    assert_error(client.get("/api/plans/demo-run-does-not-exist"), 404, "NOT_FOUND")


def test_foreign_browser_origin_cannot_mutate(client, planning_request):
    response = client.post("/api/plans", json=planning_request,
                           headers={"Origin": "https://attacker.example"})
    assert_error(response, 403, "ORIGIN_NOT_ALLOWED")


def test_other_sessions_cannot_read_or_reuse_a_run(client, planning_request):
    result = completed_result(client, planning_request)
    with new_client() as intruder:
        start_session(intruder)
        assert_error(intruder.get(f"/api/plans/{result['runId']}"), 404, "NOT_FOUND")
        assert_error(intruder.post("/api/cart/preview", json=plan_ref(result)), 404, "NOT_FOUND")


def test_worker_failure_is_reported_in_snapshot(client, planning_request):
    run = start_plan(client, planning_request, scenario="failed")
    assert run["status"] == "failed" and run["result"] is None
    assert run["error"]["code"] and run["error"]["message"]
    assert isinstance(run["error"]["retryable"], bool)


def test_small_budget_is_reported_honestly(client, planning_request):
    result = completed_result(client, {**planning_request, "budgetMinor": 100})
    assert result["budgetStatus"] == "over_budget"
    assert result["budgetRemainingMinor"] < 0
    assert result["canConfirmCart"] is False
    assert len(result["mealPlan"]) == planning_request["days"] * 3, "meals must not be dropped silently"


def test_over_budget_plan_cannot_reach_the_cart(client, planning_request):
    result = completed_result(client, {**planning_request, "budgetMinor": 100})
    response = client.post("/api/cart/preview", json=plan_ref(result))
    assert response.status_code == 409, response.text
    assert response.json()["error"]["retryable"] is False


def test_stale_version_cannot_be_previewed(client, planning_request):
    result = completed_result(client, planning_request)
    response = client.post("/api/cart/preview", json={**plan_ref(result), "version": 2})
    assert_error(response, 409, "STALE_PLAN")


@pytest.mark.parametrize("scenario", ["partial", "failed"])
def test_cart_failures_are_reported_per_item(client, planning_request, scenario):
    result = completed_result(client, planning_request)
    response = client.post("/api/cart/preview", json=plan_ref(result),
                           headers={"X-Demo-Scenario": scenario})
    assert response.status_code == 200, response.text
    preview = response.json()
    response = client.post("/api/cart/confirm",
                           json={"previewId": preview["previewId"], "idempotencyKey": f"e2e-{scenario}"})
    assert response.status_code == 200, response.text
    receipt = response.json()
    assert receipt["status"] == scenario
    statuses = [item["status"] for item in receipt["items"]]
    if scenario == "partial":
        assert "success" in statuses and "failed" in statuses
    else:
        assert statuses and set(statuses) == {"failed"}
    for item in receipt["items"]:
        if item["status"] == "failed":
            assert item["actualQuantity"] < item["requestedQuantity"], "a failed item was reported as added"


def test_recalculation_rejects_unknown_suggestions(client, planning_request):
    result = completed_result(client, planning_request)
    assert_error(recalculate(client, result, ["invented-suggestion"]), 400, "VALIDATION_ERROR")


def test_recalculation_invalidates_previous_cart_preview(client, planning_request):
    result = completed_result(client, planning_request)
    preview = client.post("/api/cart/preview", json=plan_ref(result)).json()
    assert recalculate(client, result).status_code == 202
    response = client.post("/api/cart/confirm",
                           json={"previewId": preview["previewId"], "idempotencyKey": "e2e-stale"})
    assert_error(response, 409, "STALE_PLAN")


def test_recalculation_returns_next_version(client, planning_request):
    result = completed_result(client, planning_request)
    response = recalculate(client, result)
    assert response.status_code == 202, response.text
    run = poll_run(client, response.json()["runId"])
    assert run["status"] == "completed", run["error"]
    assert run["result"]["version"] == 2
    assert run["result"]["effectiveRequest"] == planning_request


def test_fatsecret_unmatched_food_blocks_confirmation(client, planning_request):
    result = completed_result(client, planning_request)
    response = client.post("/api/fatsecret/exports/preview",
                           json={**plan_ref(result), "mealIds": [result["mealPlan"][0]["id"]]},
                           headers={"X-Demo-Scenario": "unmatched"})
    assert response.status_code == 200, response.text
    preview = response.json()
    assert preview["canConfirm"] is False
    assert any(meal["unresolved"] for meal in preview["meals"])
    response = client.post("/api/fatsecret/exports/confirm",
                           json={"previewId": preview["previewId"], "idempotencyKey": "e2e-unmatched"})
    assert_error(response, 409, "UNRESOLVED_FOODS")


@pytest.mark.parametrize(("scenario", "meal_statuses"), [
    ("partial", ["saved", "failed"]),
    ("failed", ["failed", "failed"]),
])
def test_fatsecret_export_reports_each_meal(client, planning_request, scenario, meal_statuses):
    result = completed_result(client, planning_request)
    meal_ids = [meal["id"] for meal in result["mealPlan"][:2]]
    response = client.post("/api/fatsecret/exports/preview",
                           json={**plan_ref(result), "mealIds": meal_ids},
                           headers={"X-Demo-Scenario": scenario})
    assert response.status_code == 200, response.text
    accepted = client.post("/api/fatsecret/exports/confirm",
                           json={"previewId": response.json()["previewId"],
                                 "idempotencyKey": f"e2e-export-{scenario}"})
    assert accepted.status_code == 202, accepted.text
    export = poll_export(client, accepted.json()["exportId"])
    assert export["status"] == scenario, export
    assert [meal["status"] for meal in export["meals"]] == meal_statuses
    assert all(meal["savedMealId"] is None for meal in export["meals"] if meal["status"] == "failed")


def test_other_sessions_cannot_read_an_export(client, planning_request):
    result = completed_result(client, planning_request)
    preview = client.post("/api/fatsecret/exports/preview",
                          json={**plan_ref(result), "mealIds": [result["mealPlan"][0]["id"]]}).json()
    accepted = client.post("/api/fatsecret/exports/confirm",
                           json={"previewId": preview["previewId"], "idempotencyKey": "e2e-owner"})
    assert accepted.status_code == 202, accepted.text
    with new_client() as intruder:
        start_session(intruder)
        response = intruder.get(f"/api/fatsecret/exports/{accepted.json()['exportId']}")
        assert_error(response, 404, "NOT_FOUND")
