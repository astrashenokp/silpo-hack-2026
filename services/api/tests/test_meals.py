import pytest

from smart_basket.meals import build_meal_plan, replan_meal_plan, supported_labels
from smart_basket.meals.edamam import (
    EdamamSettings,
    EdamamUnavailable,
    build_edamam_payload,
    collect_assignments,
    map_edamam_plan_response,
)
from smart_basket.meals.filters import UnsupportedMealFilter, resolve_meal_filters
from smart_basket.meals.normalization import (
    UnitNormalizationError,
    aggregate_ingredients_from_meals,
    normalize_unit,
)
from smart_basket.schemas import IngredientAmount, Pet, PlanningRequest, UserContext


def request(
    days=4,
    people=3,
    calories=2000,
    preferences=None,
    restrictions=None,
    health_conditions=None,
    cooking_time_limit=None,
):
    return PlanningRequest(
        budget_minor=180000,
        currency="UAH",
        days=days,
        people=people,
        calories_per_person_per_day=calories,
        health_conditions=[] if health_conditions is None else health_conditions,
        cooking_time_limit=cooking_time_limit,
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
    assert all(meal.macros_per_serving is not None for meal in meals)
    assert all(meal.cooking_time_minutes is not None for meal in meals)


def test_synthetic_plan_exposes_chrononutrition_calorie_targets():
    result = build_meal_plan(request(days=1, people=2, calories=2000), context())
    by_slot = {meal.slot: meal for meal in result["meals"]}

    assert by_slot["breakfast"].calorie_target.target_kcal_per_serving == 500
    assert by_slot["lunch"].calorie_target.target_kcal_per_serving == 700
    assert by_slot["dinner"].calorie_target.target_kcal_per_serving == 800
    assert result["nutrition_summary"].distribution[0].slot == "breakfast"
    assert result["nutrition_summary"].daily[0].planned_kcal_per_person == 1860
    assert result["nutrition_summary"].daily[0].within_target_range is True


def test_synthetic_plan_warns_when_daily_calories_miss_target_range():
    result = build_meal_plan(request(days=1, people=1, calories=3000), context())

    assert result["nutrition_summary"].daily[0].within_target_range is False
    assert "outside the configured +/-10%" in " ".join(result["warnings"])


def test_meal_plan_without_calorie_target_keeps_summary_nullable():
    result = build_meal_plan(request(days=1, people=1, calories=None), context())

    assert all(meal.calorie_target is None for meal in result["meals"])
    assert result["nutrition_summary"].calorie_target_kcal_per_person_per_day is None
    assert result["nutrition_summary"].daily[0].within_target_range is None


def test_meal_plan_warnings_cover_cooking_and_vision_accuracy_boundaries():
    result = build_meal_plan(request(days=1, people=1), context())
    warnings = " ".join(result["warnings"])

    assert "cooking yield" in warnings
    assert "Vision-based consumed-food analysis is outside this planner boundary" in warnings


def test_synthetic_plan_exposes_macros_and_cooking_time():
    result = build_meal_plan(request(days=1, people=1), context())
    breakfast = next(meal for meal in result["meals"] if meal.slot == "breakfast")

    assert breakfast.macros_per_serving.protein_g == 13.5
    assert breakfast.macros_per_serving.fat_g == 7.0
    assert breakfast.macros_per_serving.carbs_g == 69.0
    assert breakfast.cooking_time_minutes == 12


def test_health_conditions_and_cooking_limit_are_retained_as_warnings():
    result = build_meal_plan(
        request(
            days=1,
            people=1,
            health_conditions=["diabetes", "hypercholesterolemia"],
            cooking_time_limit=10,
        ),
        context(),
    )
    warnings = " ".join(result["warnings"])

    assert "Diabetes condition is retained" in warnings
    assert "Hypercholesterolemia condition is retained" in warnings
    assert "10-minute cooking limit" in warnings


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
    assert payload["plan"]["fit"]["ENERC_KCAL"] == {"min": 1800, "max": 2200}


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
    assert breakfast.calorie_target.target_kcal_per_serving == 500
    assert breakfast.ingredient_amounts[0].quantity == 100
    assert breakfast.macros_per_serving.protein_g == 12.5
    assert breakfast.macros_per_serving.fat_g == 5.0
    assert breakfast.macros_per_serving.carbs_g == 55.0
    assert breakfast.cooking_time_minutes == 20

    ingredient = result["ingredients"][0]
    assert ingredient.quantity == 300
    assert ingredient.unit == "g"
    assert ingredient.restrictions == ["peanut-free"]
    assert result["nutrition_summary"].daily[0].planned_kcal_per_person == 600


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


def test_replan_requested_edamam_source_declares_synthetic_fallback(monkeypatch):
    initial = build_meal_plan(request(days=1, people=1), context())
    monkeypatch.setenv("SMART_BASKET_MEALS_SOURCE", "edamam")
    monkeypatch.setenv("EDAMAM_MEAL_PLANNER_APP_ID", "app")
    monkeypatch.setenv("EDAMAM_MEAL_PLANNER_APP_KEY", "key")
    monkeypatch.setenv("EDAMAM_ACCOUNT_USER", "user")

    result = replan_meal_plan(
        request(days=1, people=1),
        context(),
        previous_meals=initial["meals"],
        reason="upgrade_plan",
    )

    assert result["source"] == "synthetic"
    assert "Live Edamam provider-side replanning is not supported yet" in result["warnings"][0]


def test_replan_requested_edamam_source_can_fail_without_fallback(monkeypatch):
    initial = build_meal_plan(request(days=1, people=1), context())
    monkeypatch.setenv("SMART_BASKET_MEALS_SOURCE", "edamam")
    monkeypatch.setenv("EDAMAM_SYNTHETIC_FALLBACK", "false")

    with pytest.raises(EdamamUnavailable):
        replan_meal_plan(
            request(days=1, people=1),
            context(),
            previous_meals=initial["meals"],
            reason="upgrade_plan",
        )


def test_unknown_meal_source_fails_explicitly(monkeypatch):
    monkeypatch.setenv("SMART_BASKET_MEALS_SOURCE", "typo")

    with pytest.raises(EdamamUnavailable):
        build_meal_plan(request(), context())


def test_unknown_units_are_not_guessed():
    with pytest.raises(UnitNormalizationError):
        normalize_unit("cup")


def test_ingredient_aggregation_rejects_mixed_units_for_same_id():
    initial = build_meal_plan(request(days=1, people=1), context())
    breakfast = next(meal for meal in initial["meals"] if meal.slot == "breakfast")
    lunch = next(meal for meal in initial["meals"] if meal.slot == "lunch")
    shared_breakfast = breakfast.model_copy(
        update={
            "ingredient_ids": ["shared"],
            "ingredient_amounts": [
                IngredientAmount(
                    ingredient_id="shared",
                    name="Shared ingredient",
                    quantity=100.0,
                    unit="g",
                )
            ],
        }
    )
    shared_lunch = lunch.model_copy(
        update={
            "ingredient_ids": ["shared"],
            "ingredient_amounts": [
                IngredientAmount(
                    ingredient_id="shared",
                    name="Shared ingredient",
                    quantity=100.0,
                    unit="ml",
                )
            ],
        }
    )

    with pytest.raises(UnitNormalizationError, match="incompatible units"):
        aggregate_ingredients_from_meals([shared_breakfast, shared_lunch], ())


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
            "totalTime": 20,
            "totalNutrients": {
                "PROCNT": {"quantity": 50},
                "FAT": {"quantity": 20},
                "CHOCDF": {"quantity": 220},
            },
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


# ---------------------------------------------------------------------------
# New dietary label coverage
# ---------------------------------------------------------------------------

def test_vegan_preference_maps_to_edamam_health_label():
    filters = resolve_meal_filters(
        request(preferences=["vegan"], restrictions=[]),
        context(),
    )
    assert filters.preferences == ("vegan",)
    assert "vegan" in filters.edamam_health_labels


def test_paleo_preference_maps_to_edamam_health_label():
    filters = resolve_meal_filters(
        request(preferences=["paleo"], restrictions=[]),
        context(),
    )
    assert "paleo" in filters.edamam_health_labels


def test_new_restrictions_map_to_edamam_health_labels():
    for label in ("gluten-free", "dairy-free", "tree-nut-free", "shellfish-free", "soy-free", "egg-free", "pork-free"):
        filters = resolve_meal_filters(
            request(preferences=[], restrictions=[label]),
            context(),
        )
        assert label in filters.edamam_health_labels, f"{label} missing from edamam labels"
        assert filters.restrictions == (label,)


def test_combined_preferences_and_restrictions_produce_correct_edamam_labels():
    filters = resolve_meal_filters(
        request(preferences=["vegan", "high-protein"], restrictions=["gluten-free", "tree-nut-free"]),
        context(),
    )
    assert set(filters.edamam_health_labels) == {"vegan", "high-protein", "gluten-free", "tree-nut-free"}


def test_unsupported_preference_from_context_fails_closed():
    with pytest.raises(UnsupportedMealFilter, match="Unsupported meal preferences"):
        resolve_meal_filters(request(preferences=[]), context(preferences=["keto"]))


def test_unsupported_restriction_from_context_still_fails_closed_with_expanded_set():
    with pytest.raises(UnsupportedMealFilter, match="Unsupported hard restrictions"):
        resolve_meal_filters(request(preferences=[], restrictions=[]), context(restrictions=["alcohol-free"]))


# ---------------------------------------------------------------------------
# Boundary tests: max and min plan sizes
# ---------------------------------------------------------------------------

def test_max_boundary_fourteen_days_six_people():
    result = build_meal_plan(request(days=14, people=6), context())
    meals = result["meals"]
    assert len(meals) == 42
    assert {meal.day for meal in meals} == set(range(1, 15))
    assert all(meal.servings == 6 for meal in meals)
    assert len({meal.title for meal in meals}) == 42


def test_min_boundary_one_day_one_person():
    result = build_meal_plan(request(days=1, people=1), context())
    meals = result["meals"]
    assert len(meals) == 3
    assert {meal.slot for meal in meals} == {"breakfast", "lunch", "dinner"}
    assert all(meal.servings == 1 for meal in meals)
    for meal in meals:
        for amount in meal.ingredient_amounts:
            assert amount.quantity > 0


def test_no_calorie_target_still_produces_meals_and_warning():
    result = build_meal_plan(request(days=2, people=2, calories=None), context())
    assert len(result["meals"]) == 6
    warnings_text = " ".join(result["warnings"])
    assert "calorie" not in warnings_text.lower() or result["source"] == "synthetic"


def test_high_protein_and_high_fiber_preferences_produce_edamam_payload():
    filters = resolve_meal_filters(
        request(preferences=["high-protein", "high-fiber"], restrictions=[]),
        context(),
    )
    assert set(filters.edamam_health_labels) == {"high-protein", "high-fiber"}
    payload = build_edamam_payload(request(preferences=["high-protein", "high-fiber"], calories=None), filters)
    health = payload["plan"]["accept"]["all"][0]["health"]
    assert "high-protein" in health and "high-fiber" in health


def test_edamam_payload_carries_all_new_restriction_labels():
    filters = resolve_meal_filters(
        request(preferences=[], restrictions=["gluten-free", "soy-free"]),
        context(),
    )
    payload = build_edamam_payload(request(preferences=[], calories=None), filters)
    health = payload["plan"]["accept"]["all"][0]["health"]
    assert "gluten-free" in health
    assert "soy-free" in health


def test_vegan_plus_restrictions_deduplication_in_edamam_payload():
    filters = resolve_meal_filters(
        request(preferences=["vegan"], restrictions=["dairy-free", "egg-free"]),
        context(preferences=["vegan"]),
    )
    assert filters.preferences == ("vegan",)
    assert set(filters.edamam_health_labels) == {"vegan", "dairy-free", "egg-free"}


def test_supported_labels_returns_complete_preference_and_restriction_lists():
    labels = supported_labels()
    assert set(labels["preferences"]) == {"vegetarian", "vegan", "paleo", "high-protein", "high-fiber"}
    assert set(labels["restrictions"]) == {
        "peanut-free", "gluten-free", "dairy-free", "tree-nut-free",
        "shellfish-free", "soy-free", "egg-free", "pork-free",
    }


def test_reduce_cost_replan_preserves_requested_meal_slots():
    initial = build_meal_plan(request(days=2, people=2), context())

    replanned = replan_meal_plan(
        request(days=2, people=2),
        context(),
        previous_meals=initial["meals"],
        reason="reduce_cost",
        preserve_meal_slots=["breakfast"],
    )

    original_breakfasts = [
        meal for meal in initial["meals"]
        if meal.slot == "breakfast"
    ]
    replanned_breakfasts = [
        meal for meal in replanned["meals"]
        if meal.slot == "breakfast"
    ]
    assert replanned_breakfasts == original_breakfasts

    initial_lentils = next(
        ingredient.quantity for ingredient in initial["ingredients"]
        if ingredient.id == "lentils"
    )
    replanned_lentils = next(
        ingredient.quantity for ingredient in replanned["ingredients"]
        if ingredient.id == "lentils"
    )
    assert replanned_lentils < initial_lentils
    assert replanned["nutrition_summary"].daily
    assert replanned["source"] == "synthetic"


def test_reduce_cost_replan_changes_all_slots_without_preservation():
    initial = build_meal_plan(request(days=1, people=2), context())

    replanned = replan_meal_plan(
        request(days=1, people=2),
        context(),
        previous_meals=initial["meals"],
        reason="reduce_cost",
    )

    initial_by_slot = {meal.slot: meal for meal in initial["meals"]}
    replanned_by_slot = {meal.slot: meal for meal in replanned["meals"]}

    for slot, initial_meal in initial_by_slot.items():
        replanned_meal = replanned_by_slot[slot]
        assert replanned_meal.title.startswith("Budget ")
        assert replanned_meal != initial_meal
        assert replanned_meal.kcal_per_serving < initial_meal.kcal_per_serving
        for before, after in zip(
            initial_meal.ingredient_amounts,
            replanned_meal.ingredient_amounts,
            strict=True,
        ):
            assert after.quantity < before.quantity


def test_replan_rejects_unknown_preserve_slots():
    initial = build_meal_plan(request(days=1, people=1), context())

    with pytest.raises(ValueError, match="Unsupported preserve_meal_slots"):
        replan_meal_plan(
            request(days=1, people=1),
            context(),
            previous_meals=initial["meals"],
            reason="reduce_cost",
            preserve_meal_slots=["snidanok"],
        )


def test_replace_ingredient_replan_removes_requested_ingredient():
    initial = build_meal_plan(request(days=1, people=2), context())

    replanned = replan_meal_plan(
        request(days=1, people=2),
        context(),
        previous_meals=initial["meals"],
        reason="replace_ingredient",
        replace_ingredient="Dry rice",
    )

    assert "rice" not in {ingredient.id for ingredient in replanned["ingredients"]}
    assert {ingredient.id for ingredient in replanned["ingredients"]} == {"oats", "lentils"}
    for meal in replanned["meals"]:
        assert "rice" not in meal.ingredient_ids
        assert all(amount.name != "Dry rice" for amount in meal.ingredient_amounts)


def test_replace_ingredient_replan_requires_target_ingredient():
    initial = build_meal_plan(request(days=1, people=1), context())

    with pytest.raises(ValueError, match="replace_ingredient is required"):
        replan_meal_plan(
            request(days=1, people=1),
            context(),
            previous_meals=initial["meals"],
            reason="replace_ingredient",
        )


def test_replace_ingredient_replan_rejects_missing_target():
    initial = build_meal_plan(request(days=1, people=1), context())

    with pytest.raises(ValueError, match="was not found"):
        replan_meal_plan(
            request(days=1, people=1),
            context(),
            previous_meals=initial["meals"],
            reason="replace_ingredient",
            replace_ingredient="Dry buckwheat",
        )


def test_replace_unknown_ingredient_uses_same_meal_alternative():
    initial = build_meal_plan(request(days=1, people=1), context())
    breakfast = next(meal for meal in initial["meals"] if meal.slot == "breakfast")
    custom_breakfast = breakfast.model_copy(
        update={
            "title": "Tofu bean breakfast",
            "ingredient_ids": ["tofu", "beans"],
            "ingredient_amounts": [
                IngredientAmount(
                    ingredient_id="tofu",
                    name="Firm tofu",
                    quantity=120.0,
                    unit="g",
                ),
                IngredientAmount(
                    ingredient_id="beans",
                    name="White beans",
                    quantity=80.0,
                    unit="g",
                ),
            ],
        }
    )
    previous_meals = [
        custom_breakfast if meal.slot == "breakfast" else meal
        for meal in initial["meals"]
    ]

    replanned = replan_meal_plan(
        request(days=1, people=1),
        context(),
        previous_meals=previous_meals,
        reason="replace_ingredient",
        replace_ingredient="Firm tofu",
    )

    breakfast_after = next(meal for meal in replanned["meals"] if meal.slot == "breakfast")
    amounts = {
        amount.ingredient_id: amount.quantity
        for amount in breakfast_after.ingredient_amounts
    }
    assert "tofu" not in amounts
    assert amounts["beans"] == 200.0


def test_replace_ingredient_takes_precedence_over_preserving_conflicting_slot():
    initial = build_meal_plan(request(days=1, people=1), context())
    original_lunch = next(meal for meal in initial["meals"] if meal.slot == "lunch")

    replanned = replan_meal_plan(
        request(days=1, people=1),
        context(),
        previous_meals=initial["meals"],
        reason="replace_ingredient",
        preserve_meal_slots=["lunch"],
        replace_ingredient="Dry rice",
    )

    replanned_lunch = next(meal for meal in replanned["meals"] if meal.slot == "lunch")
    assert replanned_lunch != original_lunch
    assert "rice" not in replanned_lunch.ingredient_ids
    assert "rice" not in {ingredient.id for ingredient in replanned["ingredients"]}


def test_upgrade_plan_replan_changes_unpreserved_meals_and_keeps_constraints():
    initial = build_meal_plan(request(days=2, people=3, calories=2000), context())

    replanned = replan_meal_plan(
        request(days=2, people=3, calories=2000),
        context(),
        previous_meals=initial["meals"],
        reason="upgrade_plan",
        preserve_meal_slots=["breakfast"],
    )

    assert [
        meal for meal in replanned["meals"] if meal.slot == "breakfast"
    ] == [
        meal for meal in initial["meals"] if meal.slot == "breakfast"
    ]
    assert {
        meal.title for meal in replanned["meals"] if meal.slot != "breakfast"
    } != {
        meal.title for meal in initial["meals"] if meal.slot != "breakfast"
    }
    assert all(meal.servings == 3 for meal in replanned["meals"])
    assert replanned["nutrition_summary"].calorie_target_kcal_per_person_per_day == 2000
    assert {ingredient.id for ingredient in replanned["ingredients"]} <= {"oats", "rice", "lentils"}


def test_upgrade_plan_replan_changes_all_slots_without_preservation():
    initial = build_meal_plan(request(days=1, people=2), context())

    replanned = replan_meal_plan(
        request(days=1, people=2),
        context(),
        previous_meals=initial["meals"],
        reason="upgrade_plan",
    )

    initial_by_slot = {meal.slot: meal for meal in initial["meals"]}
    replanned_by_slot = {meal.slot: meal for meal in replanned["meals"]}

    for slot, initial_meal in initial_by_slot.items():
        replanned_meal = replanned_by_slot[slot]
        assert replanned_meal.title.startswith("Upgraded ")
        assert replanned_meal != initial_meal
        assert replanned_meal.kcal_per_serving > initial_meal.kcal_per_serving
