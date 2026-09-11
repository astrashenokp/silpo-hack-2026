"""Meal-level replanning helpers used by Sofiia's public boundary."""

from __future__ import annotations

from typing import Literal

from smart_basket.schemas import IngredientAmount, Meal, MealMacros

from .normalization import aggregate_ingredients_from_meals
from .nutrition import (
    ACCURACY_WARNINGS,
    build_nutrition_summary,
    calorie_target_warnings,
    planning_constraint_warnings,
)
from .synthetic import build_synthetic_meal_plan

ReplanReason = Literal["reduce_cost", "replace_ingredient", "upgrade_plan"]

SUPPORTED_REPLAN_REASONS: set[str] = {
    "reduce_cost",
    "replace_ingredient",
    "upgrade_plan",
}


def build_synthetic_replanned_meal_plan(
    *,
    request,
    filters,
    previous_meals,
    reason: ReplanReason,
    preserve_meal_slots: list[str] | None = None,
    replace_ingredient: str | None = None,
):
    if reason not in SUPPORTED_REPLAN_REASONS:
        raise ValueError(
            "Unsupported meal replan reason: "
            f"{reason}. Expected one of: "
            + ", ".join(sorted(SUPPORTED_REPLAN_REASONS))
        )

    preserve_slots = set(preserve_meal_slots or [])
    generated = _generated_replan_meals(request, filters, reason, replace_ingredient)
    previous_by_position = {
        (meal.day, meal.slot): meal
        for meal in previous_meals or []
    }

    meals: list[Meal] = []
    for meal in generated:
        previous = previous_by_position.get((meal.day, meal.slot))
        if previous is not None and _should_preserve(previous, preserve_slots, replace_ingredient):
            meals.append(previous)
        else:
            meals.append(meal)

    ingredients = aggregate_ingredients_from_meals(
        meals,
        filters.restrictions,
    )
    nutrition_summary = build_nutrition_summary(request, meals)
    warnings = [
        f"Meal plan was replanned for reason '{reason}' using Sofiia synthetic fallback.",
        "Replan changes meal composition only; product matching, basket pricing and cart updates happen downstream.",
        *ACCURACY_WARNINGS,
        *planning_constraint_warnings(request, meals),
        *calorie_target_warnings(nutrition_summary),
    ]
    if preserve_slots:
        warnings.append(
            "Preserved meal slots: "
            + ", ".join(sorted(preserve_slots))
            + "."
        )
    if reason == "replace_ingredient" and replace_ingredient:
        warnings.append(
            f"Requested ingredient replacement applied at meal level: {replace_ingredient}."
        )

    sources = {meal.source for meal in meals}
    source = sources.pop() if len(sources) == 1 else "mixed"
    return {
        "meals": meals,
        "nutrition_summary": nutrition_summary,
        "ingredients": ingredients,
        "warnings": warnings,
        "source": source,
    }


def _generated_replan_meals(request, filters, reason: str, replace_ingredient: str | None) -> list[Meal]:
    template_offset = 3 if reason == "upgrade_plan" else 0
    result = build_synthetic_meal_plan(request, filters, template_offset=template_offset)
    meals = list(result["meals"])

    if reason == "reduce_cost":
        return [_reduce_cost_meal(meal) for meal in meals]
    if reason == "replace_ingredient":
        if not replace_ingredient:
            return meals
        return [_replace_ingredient_in_meal(meal, replace_ingredient) for meal in meals]
    return [_upgrade_meal(meal) for meal in meals]


def _should_preserve(
    meal: Meal,
    preserve_slots: set[str],
    replace_ingredient: str | None,
) -> bool:
    if meal.slot not in preserve_slots:
        return False
    if replace_ingredient and _meal_contains_ingredient(meal, replace_ingredient):
        return False
    return True


def _reduce_cost_meal(meal: Meal) -> Meal:
    amounts = []
    changed = False
    for amount in meal.ingredient_amounts:
        if amount.ingredient_id == "lentils":
            amounts.append(_scale_amount(amount, 0.72))
            changed = True
        else:
            amounts.append(amount)

    if changed:
        meal = _with_amounts(
            meal,
            amounts,
            title=f"Budget {meal.title.removeprefix('Budget ')}",
            kcal_factor=0.94,
            macros_factor=0.94,
        )
    return meal


def _replace_ingredient_in_meal(meal: Meal, requested: str) -> Meal:
    if not _meal_contains_ingredient(meal, requested):
        return meal

    replacement_id, replacement_name = _replacement_for(requested)
    amounts_by_id: dict[str, IngredientAmount] = {}
    for amount in meal.ingredient_amounts:
        if _matches_ingredient(amount, requested):
            replacement = IngredientAmount(
                ingredient_id=replacement_id,
                name=replacement_name,
                quantity=amount.quantity,
                unit=amount.unit,
            )
            amounts_by_id[replacement_id] = _combine_amounts(
                amounts_by_id.get(replacement_id),
                replacement,
            )
        else:
            amounts_by_id[amount.ingredient_id] = _combine_amounts(
                amounts_by_id.get(amount.ingredient_id),
                amount,
            )

    return _with_amounts(
        meal,
        list(amounts_by_id.values()),
        title=f"Alternative {meal.title.removeprefix('Alternative ')}",
        kcal_factor=0.98,
        macros_factor=0.98,
    )


def _upgrade_meal(meal: Meal) -> Meal:
    if meal.slot == "breakfast":
        amounts = [
            _scale_amount(amount, 1.08 if amount.ingredient_id == "oats" else 1.0)
            for amount in meal.ingredient_amounts
        ]
    else:
        amounts = [
            _scale_amount(amount, 1.12 if amount.ingredient_id == "lentils" else 1.0)
            for amount in meal.ingredient_amounts
        ]
    return _with_amounts(
        meal,
        amounts,
        title=f"Upgraded {meal.title.removeprefix('Upgraded ')}",
        kcal_factor=1.04,
        macros_factor=1.05,
    )


def _with_amounts(
    meal: Meal,
    amounts: list[IngredientAmount],
    *,
    title: str,
    kcal_factor: float,
    macros_factor: float,
) -> Meal:
    return meal.model_copy(
        update={
            "title": title,
            "ingredient_ids": [amount.ingredient_id for amount in amounts],
            "ingredient_amounts": amounts,
            "kcal_per_serving": _scale_optional(meal.kcal_per_serving, kcal_factor),
            "macros_per_serving": _scale_macros(meal.macros_per_serving, macros_factor),
        }
    )


def _scale_amount(amount: IngredientAmount, factor: float) -> IngredientAmount:
    return amount.model_copy(
        update={
            "quantity": round(amount.quantity * factor, 2),
        }
    )


def _combine_amounts(
    current: IngredientAmount | None,
    incoming: IngredientAmount,
) -> IngredientAmount:
    if current is None:
        return incoming
    return current.model_copy(
        update={
            "quantity": round(current.quantity + incoming.quantity, 2),
        }
    )


def _scale_optional(value: float | None, factor: float) -> float | None:
    if value is None:
        return None
    return round(value * factor, 2)


def _scale_macros(macros: MealMacros | None, factor: float) -> MealMacros | None:
    if macros is None:
        return None
    return MealMacros(
        protein_g=round(macros.protein_g * factor, 2),
        fat_g=round(macros.fat_g * factor, 2),
        carbs_g=round(macros.carbs_g * factor, 2),
    )


def _meal_contains_ingredient(meal: Meal, requested: str) -> bool:
    return any(_matches_ingredient(amount, requested) for amount in meal.ingredient_amounts)


def _matches_ingredient(amount: IngredientAmount, requested: str) -> bool:
    normalized = requested.strip().casefold()
    return normalized in {
        amount.ingredient_id.casefold(),
        amount.name.casefold(),
    }


def _replacement_for(requested: str) -> tuple[str, str]:
    normalized = requested.strip().casefold()
    if normalized in {"rice", "dry rice"}:
        return "lentils", "Dry lentils"
    if normalized in {"lentils", "dry lentils"}:
        return "rice", "Dry rice"
    return "rice", "Dry rice"
