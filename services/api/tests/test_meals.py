import pytest

from smart_basket.meals import build_meal_plan
from smart_basket.meals.edamam import (
    EdamamSettings,
    EdamamUnavailable,
    build_edamam_payload,
    collect_assignments,
    map_edamam_plan_response,
)
from smart_basket.meals.filters import UnsupportedMealFilter, resolve_meal_filters
from smart_basket.meals.normalization import UnitNormalizationError, normalize_unit
from smart_basket.schemas import Pet, PlanningRequest, UserContext


def request(days=4, people=3, calories=2000, preferences=None, restrictions=None):
    return PlanningRequest(
        budget_minor=180000,
        currency="UAH",
        days=days,
        people=people,
        calories_per_person_per_day=calories,
        preferences=["vegetarian"] if preferences is None else preferences,
        restrictions=[] if restrictions is None else restrictions,
        pets=[Pet(species="cat", count=1)],
        include_recurring=True,
        notes="",
    )


def context(preferences=None, restrictions=None):
    return UserContext(
        preferences=[] if preferences is None else preferences,
        restrictions=[] if restrictions is None else restrictions,
        pets=[],
        history_available=False,
        cart_context_ready=True,
        warnings=[],
    )


def test_synthetic_plan_covers_every_day_and_slot():
    result = build_meal_plan(request(), context())
    meals = result["meals"]

    assert len(meals) == 12
    assert {(meal.day, meal.slot) for meal in meals} == {
        (day, slot)
        for day in range(1, 5)
        for slot in ("breakfast", "lunch", "dinner")
    }
    assert {meal.source for meal in meals} == {"synthetic"}
    assert all(meal.servings == 3 for meal in meals)
    assert all(meal.kcal_per_serving is not None for meal in meals)


def test_synthetic_plan_has_demo_variety_without_changing_totals():
    result = build_meal_plan(request(), context())
    titles = {meal.title for meal in result["meals"]}
    quantities = {ingredient.id: ingredient.quantity for ingredient in result["ingredients"]}

    assert len(titles) > 3
    assert quantities == {"oats": 600, "rice": 1440, "lentils": 1200}


def test_serving_scaling_and_aggregate_quantities_are_consistent():
    result = build_meal_plan(request(days=2, people=3), context())
    by_meal = {meal.id: meal for meal in result["meals"]}
    breakfast = by_meal["synthetic-day-1-breakfast-1"]
    lunch = by_meal["synthetic-day-1-lunch-2"]
    dinner = by_meal["synthetic-day-1-dinner-3"]

    assert breakfast.ingredient_amounts[0].quantity == 150
    assert {amount.ingredient_id: amount.quantity for amount in lunch.ingredient_amounts} == {
        "rice": 240,
        "lentils": 90,
    }
    assert {amount.ingredient_id: amount.quantity for amount in dinner.ingredient_amounts} == {
        "lentils": 210,
        "rice": 120,
    }

    quantities = {ingredient.id: ingredient.quantity for ingredient in result["ingredients"]}
    assert quantities == {"lentils": 600, "oats": 300, "rice": 720}


def test_personal_portion_for_fatsecret_uses_meal_amount_not_aggregate():
    result = build_meal_plan(request(days=1, people=3), context())
    lunch = next(meal for meal in result["meals"] if meal.slot == "lunch")

    personal = {
        amount.ingredient_id: amount.quantity / lunch.servings
        for amount in lunch.ingredient_amounts
    }
    assert personal == {"rice": 80, "lentils": 30}


def test_context_and_request_filters_merge_and_map_to_edamam_labels():
    filters = resolve_meal_filters(
        request(preferences=[], restrictions=["peanut-free"]),
        context(preferences=["vegetarian"], restrictions=["peanut-free"]),
    )

    assert filters.preferences == ("vegetarian",)
    assert filters.restrictions == ("peanut-free",)
    assert filters.edamam_health_labels == ("vegetarian", "peanut-free")


def test_unsupported_context_restriction_fails_closed():
    with pytest.raises(UnsupportedMealFilter):
        resolve_meal_filters(request(), context(restrictions=["wheat-free"]))


def test_edamam_payload_retains_days_slots_filters_and_calorie_bounds():
    filters = resolve_meal_filters(request(restrictions=["peanut-free"]), context())
    payload = build_edamam_payload(request(), filters)

    assert payload["size"] == 4
    assert set(payload["plan"]["sections"]) == {"Breakfast", "Lunch", "Dinner"}
    assert payload["plan"]["accept"]["all"] == [{"health": ["vegetarian", "peanut-free"]}]
    assert payload["plan"]["fit"]["ENERC_KCAL"] == {"min": 1700, "max": 2300}


def test_edamam_settings_are_loaded_only_when_complete(monkeypatch):
    for name in (
        "EDAMAM_MEAL_PLANNER_APP_ID",
        "EDAMAM_MEAL_PLANNER_APP_KEY",
        "EDAMAM_ACCOUNT_USER",
    ):
        monkeypatch.delenv(name, raising=False)

    assert EdamamSettings.from_env() is None

    monkeypatch.setenv("EDAMAM_MEAL_PLANNER_APP_ID", "app")
    monkeypatch.setenv("EDAMAM_MEAL_PLANNER_APP_KEY", "key")
    monkeypatch.setenv("EDAMAM_ACCOUNT_USER", "user")
    monkeypatch.setenv("EDAMAM_TIMEOUT_SECONDS", "3")

    settings = EdamamSettings.from_env()
    assert settings is not None
    assert settings.app_id == "app"
    assert settings.app_key == "key"
    assert settings.account_user == "user"
    assert settings.timeout_seconds == 3


def test_edamam_settings_reject_invalid_timeout(monkeypatch):
    monkeypatch.setenv("EDAMAM_MEAL_PLANNER_APP_ID", "app")
    monkeypatch.setenv("EDAMAM_MEAL_PLANNER_APP_KEY", "key")
    monkeypatch.setenv("EDAMAM_ACCOUNT_USER", "user")
    monkeypatch.setenv("EDAMAM_TIMEOUT_SECONDS", "zero")

    with pytest.raises(EdamamUnavailable):
        EdamamSettings.from_env()


def test_edamam_payload_omits_empty_accept_filters():
    filters = resolve_meal_filters(request(preferences=[]), context())
    payload = build_edamam_payload(request(preferences=[], calories=None), filters)

    assert "accept" not in payload["plan"]
    assert "fit" not in payload["plan"]


def test_edamam_selection_and_recipe_details_map_to_contract_models():
    plan_response = _edamam_selection_response(days=1)
    filters = resolve_meal_filters(request(preferences=[], restrictions=["peanut-free"]), context())
    result = map_edamam_plan_response(
        response=plan_response,
        recipe_details={
            "recipe:breakfast": _recipe_detail("Breakfast oats", "https://recipes.test/oats"),
            "recipe:lunch": _recipe_detail("Lunch rice", "https://recipes.test/rice"),
            "recipe:dinner": _recipe_detail("Dinner lentils", "https://recipes.test/lentils"),
        },
        request_model=request(days=1, people=2, preferences=[], restrictions=["peanut-free"]),
        filters=filters,
    )

    assert result["source"] == "edamam"
    assert len(result["meals"]) == 3
    breakfast = result["meals"][0]
    assert breakfast.source == "edamam"
    assert breakfast.source_url == "https://recipes.test/oats"
    assert breakfast.attribution == "Recipe data powered by Edamam."
    assert breakfast.servings == 2
    assert breakfast.kcal_per_serving == 200
    assert breakfast.ingredient_amounts[0].quantity == 100

    ingredient = result["ingredients"][0]
    assert ingredient.quantity == 300
    assert ingredient.unit == "g"
    assert ingredient.restrictions == ["peanut-free"]


def test_edamam_mapping_rejects_incomplete_selection():
    with pytest.raises(EdamamUnavailable):
        collect_assignments({"selection": [{"sections": {"Breakfast": {}}}]})


def test_build_meal_plan_can_return_mapped_edamam_meals(monkeypatch):
    class FakeClient:
        def __init__(self, settings):
            self.settings = settings

        def request_plan(self, payload):
            return _edamam_selection_response(days=1)

        def request_recipe(self, href, uri):
            return _recipe_detail(f"Recipe {uri}", f"https://recipes.test/{uri.rsplit(':', 1)[-1]}")

    monkeypatch.setenv("SMART_BASKET_MEALS_SOURCE", "edamam")
    monkeypatch.setenv("EDAMAM_MEAL_PLANNER_APP_ID", "app")
    monkeypatch.setenv("EDAMAM_MEAL_PLANNER_APP_KEY", "key")
    monkeypatch.setenv("EDAMAM_ACCOUNT_USER", "user")
    monkeypatch.setattr("smart_basket.meals.planner.EdamamMealPlannerClient", FakeClient)

    result = build_meal_plan(request(days=1, people=2, preferences=[]), context())

    assert result["source"] == "edamam"
    assert len(result["meals"]) == 3
    assert {meal.source for meal in result["meals"]} == {"edamam"}


def test_requested_edamam_source_uses_explicit_synthetic_fallback(monkeypatch):
    monkeypatch.setenv("SMART_BASKET_MEALS_SOURCE", "edamam")
    monkeypatch.delenv("EDAMAM_MEAL_PLANNER_APP_ID", raising=False)
    monkeypatch.delenv("EDAMAM_MEAL_PLANNER_APP_KEY", raising=False)
    monkeypatch.delenv("EDAMAM_ACCOUNT_USER", raising=False)

    result = build_meal_plan(request(), context())

    assert result["source"] == "synthetic"
    assert "credentials are incomplete" in result["warnings"][0]


def test_requested_edamam_source_can_fail_without_fallback(monkeypatch):
    monkeypatch.setenv("SMART_BASKET_MEALS_SOURCE", "edamam")
    monkeypatch.setenv("EDAMAM_SYNTHETIC_FALLBACK", "false")
    monkeypatch.delenv("EDAMAM_MEAL_PLANNER_APP_ID", raising=False)
    monkeypatch.delenv("EDAMAM_MEAL_PLANNER_APP_KEY", raising=False)
    monkeypatch.delenv("EDAMAM_ACCOUNT_USER", raising=False)

    with pytest.raises(EdamamUnavailable):
        build_meal_plan(request(), context())


def test_unknown_meal_source_fails_explicitly(monkeypatch):
    monkeypatch.setenv("SMART_BASKET_MEALS_SOURCE", "typo")

    with pytest.raises(EdamamUnavailable):
        build_meal_plan(request(), context())


def test_unknown_units_are_not_guessed():
    with pytest.raises(UnitNormalizationError):
        normalize_unit("cup")


def _edamam_selection_response(days):
    return {
        "status": "OK",
        "selection": [
            {
                "sections": {
                    "Breakfast": _assignment("recipe:breakfast"),
                    "Lunch": _assignment("recipe:lunch"),
                    "Dinner": _assignment("recipe:dinner"),
                }
            }
            for _ in range(days)
        ],
    }


def _assignment(uri):
    slug = uri.rsplit(":", 1)[-1]
    return {
        "assigned": uri,
        "_links": {
            "self": {
                "title": slug.title(),
                "href": f"https://api.edamam.test/api/recipes/v2/{slug}?type=public",
            }
        },
    }


def _recipe_detail(label, url):
    return {
        "recipe": {
            "uri": f"recipe:{label}",
            "label": label,
            "url": url,
            "yield": 4,
            "calories": 800,
            "ingredients": [
                {
                    "foodId": "food-oats",
                    "food": "Dry oats",
                    "foodCategory": "grains",
                    "weight": 200,
                    "text": "Dry oats",
                },
                {
                    "foodId": "food-rice",
                    "food": "Dry rice",
                    "foodCategory": "grains",
                    "weight": 400,
                    "text": "Dry rice",
                },
            ],
        }
    }
