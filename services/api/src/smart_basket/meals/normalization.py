"""Serving scaling, unit normalization and ingredient aggregation."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Literal

from smart_basket.schemas import IngredientAmount, IngredientRequirement, Meal, MealCalorieTarget

NormalizedUnit = Literal["g", "ml", "piece"]


class UnitNormalizationError(ValueError):
    """Raised when a provider unit cannot be converted without guessing."""


@dataclass(frozen=True)
class IngredientSpec:
    id: str
    name: str
    search_terms: tuple[str, ...]
    quantity_per_serving: float
    unit: str


@dataclass(frozen=True)
class MealTemplate:
    slot: Literal["breakfast", "lunch", "dinner"]
    title: str
    kcal_per_serving: float | None
    ingredients: tuple[IngredientSpec, ...]
    source_url: str | None = None
    attribution: str | None = None


UNIT_ALIASES: dict[str, NormalizedUnit] = {
    "g": "g",
    "gram": "g",
    "grams": "g",
    "ml": "ml",
    "milliliter": "ml",
    "milliliters": "ml",
    "piece": "piece",
    "pieces": "piece",
}


def normalize_unit(unit: str) -> NormalizedUnit:
    normalized = UNIT_ALIASES.get(unit.strip().casefold())
    if normalized is None:
        raise UnitNormalizationError(
            f"Unsupported ingredient unit '{unit}'; no mass/volume is guessed."
        )
    return normalized


def build_meal_from_template(
    *,
    day: int,
    index: int,
    servings: int,
    template: MealTemplate,
    restrictions: tuple[str, ...],
    source: Literal["edamam", "synthetic"],
    calorie_target: MealCalorieTarget | None = None,
) -> Meal:
    meal_id = f"{source}-day-{day}-{template.slot}-{index}"
    amounts: list[IngredientAmount] = []
    ingredient_ids: list[str] = []

    for ingredient in template.ingredients:
        unit = normalize_unit(ingredient.unit)
        quantity = ingredient.quantity_per_serving * servings
        ingredient_ids.append(ingredient.id)
        amounts.append(
            IngredientAmount(
                ingredient_id=ingredient.id,
                name=ingredient.name,
                quantity=float(quantity),
                unit=unit,
            )
        )

    return Meal(
        id=meal_id,
        day=day,
        slot=template.slot,
        title=template.title,
        servings=servings,
        kcal_per_serving=template.kcal_per_serving,
        calorie_target=calorie_target,
        ingredient_ids=ingredient_ids,
        ingredient_amounts=amounts,
        source=source,
        source_url=template.source_url,
        attribution=template.attribution,
    )


def aggregate_ingredients(
    meals: list[Meal],
    specs: dict[str, IngredientSpec],
    restrictions: tuple[str, ...],
) -> list[IngredientRequirement]:
    quantities: dict[str, float] = defaultdict(float)
    meal_ids: dict[str, list[str]] = defaultdict(list)

    for meal in meals:
        for amount in meal.ingredient_amounts:
            quantities[amount.ingredient_id] += amount.quantity
            meal_ids[amount.ingredient_id].append(meal.id)

    ingredients: list[IngredientRequirement] = []
    for ingredient_id in quantities:
        spec = specs[ingredient_id]
        ingredients.append(
            IngredientRequirement(
                id=ingredient_id,
                name=spec.name,
                search_terms=list(spec.search_terms),
                quantity=float(quantities[ingredient_id]),
                unit=normalize_unit(spec.unit),
                meal_ids=meal_ids[ingredient_id],
                restrictions=list(restrictions),
            )
        )
    return ingredients
