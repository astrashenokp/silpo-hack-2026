from fastapi.testclient import TestClient

from conftest import create_plan
from smart_basket.app import create_app
from smart_basket.fatsecret.client import FatSecretClientError
from test_api import owner, reference


class FakeLiveFatSecret:
    def __init__(self):
        self.meals = []
        self.items = {}
        self.calls = []
        self.fail_food_id = None
        self.persist_before_failure = False
        self.ambiguous_oats = False
        self.needs_core_lentils = False

    async def delegated_call(self, session, method, parameters=None):
        parameters = dict(parameters or {})
        self.calls.append((method, parameters))
        if method == "foods.search.v5":
            name = parameters["search_expression"]
            food_id = {
                "Dry oats": "10", "Dry rice": "20", "Dry lentils": "30", "lentils": "30",
            }[name]
            def food(candidate_id, candidate_name):
                return {
                "food_id": candidate_id,
                "food_name": candidate_name,
                "food_type": "Generic",
                "servings": {"serving": {
                    "serving_id": f"{food_id}00",
                    "serving_description": "100 g dry",
                    "metric_serving_amount": "100",
                    "metric_serving_unit": "g",
                    "number_of_units": "100",
                    "measurement_description": "g",
                    "calories": "380",
                }},
            }
            foods = (
                [food("10", "Oats (Dry)"), food("11", "Dry Oats")]
                if name == "Dry oats" and self.ambiguous_oats
                else food("31", "Lentil soup")
                if name == "Dry lentils" and self.needs_core_lentils
                else food(food_id, "Lentils, raw" if name == "lentils" else name)
            )
            if isinstance(foods, list):
                foods[1]["servings"]["serving"]["serving_id"] = "1100"
            return {"foods_search": {"results": {"food": foods}}}
        if method == "saved_meals.get.v2":
            return {"saved_meals": {"saved_meal": list(self.meals)}}
        if method == "saved_meal.create":
            saved_id = str(len(self.meals) + 100)
            self.meals.append({
                "saved_meal_id": saved_id,
                "saved_meal_name": parameters["saved_meal_name"],
                "saved_meal_description": parameters["saved_meal_description"],
            })
            self.items[saved_id] = []
            return {"saved_meal_id": {"value": saved_id}}
        if method == "saved_meal_items.get.v2":
            return {"saved_meal_items": {
                "saved_meal_item": list(self.items[parameters["saved_meal_id"]])
            }}
        if method == "saved_meal_item.add":
            remote = {
                "saved_meal_item_id": str(len(self.items[parameters["saved_meal_id"]]) + 1000),
                "food_id": parameters["food_id"],
                "serving_id": parameters["serving_id"],
                "number_of_units": parameters["number_of_units"],
            }
            should_fail = parameters["food_id"] == self.fail_food_id
            if not should_fail or self.persist_before_failure:
                self.items[parameters["saved_meal_id"]].append(remote)
            if should_fail:
                raise FatSecretClientError("uncertain write")
            return {"saved_meal_item_id": {"value": remote["saved_meal_item_id"]}}
        raise AssertionError(f"Unexpected FatSecret method: {method}")

    async def start(self, owner):  # pragma: no cover - route compatibility
        raise AssertionError("not used")

    async def cancel(self, owner):  # pragma: no cover - route compatibility
        return None

    def return_url(self, *, connected):  # pragma: no cover - route compatibility
        return "http://localhost:3000"


def connected_app(provider):
    app = create_app(fatsecret_oauth=provider)
    client = TestClient(app)
    client.__enter__()
    client.get("/api/context")
    session = owner(app, client)
    session.fatsecret_connected = True
    session.fatsecret_access_token = "token"
    session.fatsecret_access_secret = "secret"
    session.fatsecret_account_label = "Rina test account"
    session.fatsecret_connection_revision = 1
    return app, client, session


def make_live_preview(client, plan, count=1):
    return client.post("/api/fatsecret/exports/preview", json={
        **reference(plan),
        "mealIds": [meal["id"] for meal in plan["mealPlan"][:count]],
    })


def test_live_export_scales_writes_reads_back_and_deduplicates(planning_request):
    provider = FakeLiveFatSecret()
    app, client, session = connected_app(provider)
    try:
        plan = create_plan(client, planning_request)
        preview_response = make_live_preview(client, plan)
        assert preview_response.status_code == 200, preview_response.text
        preview = preview_response.json()
        assert preview["accountLabel"] == "Rina test account"
        assert preview["canConfirm"] is True
        assert preview["meals"][0]["items"][0]["sourceQuantity"] == 50
        assert preview["meals"][0]["items"][0]["numberOfUnits"] == 50
        assert preview["meals"][0]["fatsecretKcalPerServing"] == 190

        accepted = client.post("/api/fatsecret/exports/confirm", json={
            "previewId": preview["previewId"], "idempotencyKey": "live-one",
        })
        export_id = accepted.json()["exportId"]
        result = client.get(f"/api/fatsecret/exports/{export_id}").json()
        assert result["status"] == "success"
        assert result["meals"][0]["status"] == "saved"
        assert result["meals"][0]["savedMealId"] == "100"

        second = make_live_preview(client, plan).json()
        repeated = client.post("/api/fatsecret/exports/confirm", json={
            "previewId": second["previewId"], "idempotencyKey": "live-two",
        })
        assert repeated.json()["exportId"] == export_id
        assert len(provider.meals) == 1
        assert len(provider.items["100"]) == 1
        assert len(session.saved_meals) == 1
    finally:
        client.__exit__(None, None, None)


def test_uncertain_item_write_is_reconciled_without_duplicate(planning_request):
    provider = FakeLiveFatSecret()
    provider.fail_food_id = "10"
    provider.persist_before_failure = True
    _, client, _ = connected_app(provider)
    try:
        plan = create_plan(client, planning_request)
        preview = make_live_preview(client, plan).json()
        accepted = client.post("/api/fatsecret/exports/confirm", json={
            "previewId": preview["previewId"], "idempotencyKey": "uncertain",
        }).json()
        result = client.get(f"/api/fatsecret/exports/{accepted['exportId']}").json()
        assert result["status"] == "success"
        assert len(provider.items["100"]) == 1
    finally:
        client.__exit__(None, None, None)


def test_partial_export_can_resume_from_a_new_reviewed_preview(planning_request):
    provider = FakeLiveFatSecret()
    provider.fail_food_id = "20"
    _, client, _ = connected_app(provider)
    try:
        plan = create_plan(client, planning_request)
        first = make_live_preview(client, plan, count=2).json()
        accepted = client.post("/api/fatsecret/exports/confirm", json={
            "previewId": first["previewId"], "idempotencyKey": "partial-one",
        }).json()
        result = client.get(f"/api/fatsecret/exports/{accepted['exportId']}").json()
        assert result["status"] == "partial"

        provider.fail_food_id = None
        second = make_live_preview(client, plan, count=2).json()
        retried = client.post("/api/fatsecret/exports/confirm", json={
            "previewId": second["previewId"], "idempotencyKey": "partial-two",
        }).json()
        assert retried["exportId"] == accepted["exportId"]
        result = client.get(f"/api/fatsecret/exports/{accepted['exportId']}").json()
        assert result["status"] == "success"
        assert len(provider.meals) == 2
        assert sorted(len(items) for items in provider.items.values()) == [1, 2]
    finally:
        client.__exit__(None, None, None)


def test_connection_change_invalidates_live_preview(planning_request):
    provider = FakeLiveFatSecret()
    _, client, session = connected_app(provider)
    try:
        plan = create_plan(client, planning_request)
        preview = make_live_preview(client, plan).json()
        session.fatsecret_connection_revision += 1
        response = client.post("/api/fatsecret/exports/confirm", json={
            "previewId": preview["previewId"], "idempotencyKey": "stale-account",
        })
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "STALE_ACCOUNT"
        assert provider.meals == []
    finally:
        client.__exit__(None, None, None)


def test_edamam_export_requires_explicit_permission(planning_request, monkeypatch):
    monkeypatch.delenv("FATSECRET_ALLOW_EDAMAM_EXPORT", raising=False)
    provider = FakeLiveFatSecret()
    _, client, session = connected_app(provider)
    try:
        plan = create_plan(client, planning_request)
        session.runs[plan["runId"]].result.meal_plan[0].source = "edamam"
        response = make_live_preview(client, plan)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "EXPORT_PERMISSION_REQUIRED"
        assert provider.calls == []
    finally:
        client.__exit__(None, None, None)


def test_reconnected_account_gets_a_distinct_export_operation(planning_request):
    provider = FakeLiveFatSecret()
    _, client, session = connected_app(provider)
    try:
        plan = create_plan(client, planning_request)
        first = make_live_preview(client, plan).json()
        first_id = client.post("/api/fatsecret/exports/confirm", json={
            "previewId": first["previewId"], "idempotencyKey": "account-one",
        }).json()["exportId"]

        session.fatsecret_connection_revision += 1
        provider.meals.clear()
        provider.items.clear()
        second = make_live_preview(client, plan).json()
        second_id = client.post("/api/fatsecret/exports/confirm", json={
            "previewId": second["previewId"], "idempotencyKey": "account-two",
        }).json()["exportId"]
        assert second_id != first_id
        assert client.get(f"/api/fatsecret/exports/{second_id}").json()["status"] == "success"
    finally:
        client.__exit__(None, None, None)


def test_equivalent_matches_resolve_automatically_and_accept_verified_selection(planning_request):
    provider = FakeLiveFatSecret()
    provider.ambiguous_oats = True
    _, client, _ = connected_app(provider)
    try:
        plan = create_plan(client, planning_request)
        first = make_live_preview(client, plan).json()
        assert first["canConfirm"] is True
        assert first["meals"][0]["unresolved"] == []

        selected = first["meals"][0]["items"][0]
        second = client.post("/api/fatsecret/exports/preview", json={
            **reference(plan),
            "mealIds": [plan["mealPlan"][0]["id"]],
            "selections": [{
                "mealId": plan["mealPlan"][0]["id"],
                "ingredientId": selected["ingredientId"],
                "foodId": selected["foodId"],
                "servingId": selected["servingId"],
            }],
        }).json()
        assert second["canConfirm"] is True
        assert second["meals"][0]["items"][0]["foodId"] == selected["foodId"]
    finally:
        client.__exit__(None, None, None)


def test_low_confidence_dry_name_retries_with_core_food_name(planning_request):
    provider = FakeLiveFatSecret()
    provider.needs_core_lentils = True
    _, client, _ = connected_app(provider)
    try:
        plan = create_plan(client, planning_request)
        preview = make_live_preview(client, plan, count=3).json()

        assert preview["canConfirm"] is True
        dinner = preview["meals"][2]
        assert dinner["unresolved"] == []
        assert dinner["items"][0]["matchedName"] == "Lentils, raw"
        expressions = [
            parameters["search_expression"]
            for method, parameters in provider.calls
            if method == "foods.search.v5"
        ]
        assert "Dry lentils" in expressions
        assert "lentils" in expressions
    finally:
        client.__exit__(None, None, None)
