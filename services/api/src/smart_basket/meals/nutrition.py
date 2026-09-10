"""Calorie target helpers for Sofiia's meal-planning contract."""

from __future__ import annotations

from collections import defaultdict

from smart_basket.schemas import (
    DayNutritionSummary,
    Meal,
    MealCalorieTarget,
    NutritionSummary,
    SlotCalorieShare,
)

CALORIE_TOLERANCE_PCT = 0.10
SLOT_CALORIE_SHARES = {
    "breakfast": 0.25,
    "lunch": 0.35,
    "dinner": 0.40,
}

ACCURACY_WARNINGS = [
    (
        "Meal calories are estimates; cooking yield, oil absorption, sauces and hidden "
        "ingredients are not recalculated from photos."
    ),
    (
        "Vision-based consumed-food analysis is outside this planner boundary and must "
        "not overwrite planned nutrition without verified measurements."
    ),
]


def calorie_target_for_slot(target_kcal: int | None, slot: str) -> MealCalorieTarget | None:
    if target_kcal is None:
        return None
    share = SLOT_CALORIE_SHARES[slot]
    target = float(target_kcal * share)
    return MealCalorieTarget(
        share=share,
        target_kcal_per_serving=target,
        min_kcal_per_serving=target * (1 - CALORIE_TOLERANCE_PCT),
        max_kcal_per_serving=target * (1 + CALORIE_TOLERANCE_PCT),
    )


def build_nutrition_summary(request, meals: list[Meal]) -> NutritionSummary:
    target = request.calories_per_person_per_day
    daily_totals: dict[int, float] = defaultdict(float)
    complete_days: dict[int, bool] = defaultdict(lambda: True)

    for meal in meals:
        if meal.kcal_per_serving is None:
            complete_days[meal.day] = False
            continue
        daily_totals[meal.day] += meal.kcal_per_serving

    daily = []
    for day in range(1, request.days + 1):
        planned = daily_totals.get(day)
        planned_value = float(planned) if complete_days[day] and planned is not None else None
        if target is None or planned_value is None:
            min_value = None
            max_value = None
            within_range = None
        else:
            min_value = float(target * (1 - CALORIE_TOLERANCE_PCT))
            max_value = float(target * (1 + CALORIE_TOLERANCE_PCT))
            within_range = min_value <= planned_value <= max_value
        daily.append(
            DayNutritionSummary(
                day=day,
                target_kcal_per_person=float(target) if target is not None else None,
                planned_kcal_per_person=planned_value,
                min_kcal_per_person=min_value,
                max_kcal_per_person=max_value,
                within_target_range=within_range,
            )
        )

    return NutritionSummary(
        calorie_target_kcal_per_person_per_day=float(target) if target is not None else None,
        tolerance_pct=CALORIE_TOLERANCE_PCT,
        distribution=[
            SlotCalorieShare(slot=slot, share=share)
            for slot, share in SLOT_CALORIE_SHARES.items()
        ],
        daily=daily,
    )


def calorie_target_warnings(summary: NutritionSummary) -> list[str]:
    warnings = []
    for day in summary.daily:
        if day.within_target_range is False:
            warnings.append(
                f"Day {day.day} planned calories are outside the configured +/-10% daily target range."
            )
    return warnings


def planning_constraint_warnings(request, meals: list[Meal]) -> list[str]:
    warnings = []
    health_conditions = set(getattr(request, "health_conditions", []) or [])
    if "diabetes" in health_conditions:
        warnings.append(
            "Diabetes condition is retained and meal macros are exposed, but this planner does not replace medical nutrition advice or glycemic-load verification."
        )
    if "hypercholesterolemia" in health_conditions:
        warnings.append(
            "Hypercholesterolemia condition is retained, but saturated fat and cholesterol constraints require verified provider nutrients before live enforcement."
        )

    cooking_time_limit = getattr(request, "cooking_time_limit", None)
    if cooking_time_limit is not None:
        over_limit = [
            meal
            for meal in meals
            if meal.cooking_time_minutes is not None
            and meal.cooking_time_minutes > cooking_time_limit
        ]
        unknown_time = [
            meal
            for meal in meals
            if meal.cooking_time_minutes is None
        ]
        if over_limit:
            warnings.append(
                f"{len(over_limit)} planned meals exceed the requested {cooking_time_limit}-minute cooking limit."
            )
        if unknown_time:
            warnings.append(
                f"{len(unknown_time)} planned meals have no verified cooking-time estimate."
            )
    return warnings
