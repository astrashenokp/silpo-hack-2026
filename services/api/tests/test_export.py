import pytest
from fastapi.testclient import TestClient

from conftest import create_plan
from test_api import owner, reference


def make_preview(client, plan, scenario="success", count=2):
    return client.post("/api/fatsecret/exports/preview", json={**reference(plan),
        "mealIds": [m["id"] for m in plan["mealPlan"][:count]]}, headers={"X-Demo-Scenario": scenario})


@pytest.mark.parametrize("scenario,expected", [("success", "success"), ("partial", "partial"), ("failed", "failed")])
def test_export_outcomes_portions_and_duplicate_protection(app, client, planning_request, scenario, expected):
    plan = create_plan(client, planning_request)
    preview = make_preview(client, plan, scenario).json()
    item = preview["meals"][0]["items"][0]
    assert item["sourceQuantity"] == 50
    assert item["numberOfUnits"] == 0.5
    lunch_items = preview["meals"][1]["items"]
    assert {item["ingredientId"]: item["sourceQuantity"] for item in lunch_items} == {
        "rice": 80,
        "lentils": 30,
    }
    assert preview["portionBasis"] == "one_person"
    assert preview["destination"] == "saved_meals"
    body = {"previewId": preview["previewId"], "idempotencyKey": "save-once"}
    accepted = client.post("/api/fatsecret/exports/confirm", json=body)
    assert accepted.status_code == 202
    export = client.get(f"/api/fatsecret/exports/{accepted.json()['exportId']}").json()
    assert export["status"] == expected
    assert client.post("/api/fatsecret/exports/confirm", json=body).json() == accepted.json()
    second_preview = make_preview(client, plan, scenario).json()
    repeated = client.post("/api/fatsecret/exports/confirm", json={"previewId": second_preview["previewId"], "idempotencyKey": "another"})
    assert repeated.json() == accepted.json()
    assert owner(app, client).cart == {"demo-existing-soap": (1, 3500)}
    with TestClient(app) as stranger:
        stranger.get("/api/context")
        assert stranger.get(f"/api/fatsecret/exports/{export['exportId']}").status_code == 404
        assert stranger.post("/api/fatsecret/exports/confirm", json=body).status_code == 404


def test_unmatched_empty_unknown_and_stale_exports(client, planning_request):
    plan = create_plan(client, planning_request)
    preview = make_preview(client, plan, "unmatched").json()
    assert not preview["canConfirm"] and preview["meals"][0]["unresolved"]
    assert client.post("/api/fatsecret/exports/confirm", json={"previewId": preview["previewId"], "idempotencyKey": "x"}).status_code == 409
    for ids in [[], ["unknown"], [plan["mealPlan"][0]["id"]] * 2]:
        assert client.post("/api/fatsecret/exports/preview", json={**reference(plan), "mealIds": ids}).status_code == 400
    preview = make_preview(client, plan).json()
    client.post(f"/api/plans/{plan['runId']}/recalculate", json={"version": 1, "selectedRecurringIds": []})
    assert client.post("/api/fatsecret/exports/confirm", json={"previewId": preview["previewId"], "idempotencyKey": "y"}).status_code == 409


def test_overlapping_selections_do_not_duplicate_saved_meal(app, client, planning_request):
    plan = create_plan(client, planning_request)
    for count in (1, 2):
        preview = make_preview(client, plan, count=count).json()
        accepted = client.post("/api/fatsecret/exports/confirm", json={"previewId": preview["previewId"], "idempotencyKey": str(count)}).json()
    export = client.get(f"/api/fatsecret/exports/{accepted['exportId']}").json()
    assert export["meals"][0]["status"] == "already_saved"
    assert export["meals"][1]["status"] == "saved"
    assert len(owner(app, client).saved_meals) == 2
