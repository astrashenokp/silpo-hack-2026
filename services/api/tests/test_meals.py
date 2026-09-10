import pytest

from smart_basket.meals import build_meal_plan
from smart_basket.meals.edamam import EdamamSettings, build_edamam_payload
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
        preferences=preferences or ["vegetarian"],
        restrictions=restrictions or [],
        pets=[Pet(species="cat", count=1)],
        include_recurring=True,
        notes="",
    )


def context(preferences=None, restrictions=None):
    return UserContext(
        preferences=preferences or [],
        restrictions=restrictions or [],
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
        resolve_meal_filters(request(), context(restrictions=["gluten-free"]))


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


def test_unknown_units_are_not_guessed():
    with pytest.raises(UnitNormalizationError):
        normalize_unit("cup")
