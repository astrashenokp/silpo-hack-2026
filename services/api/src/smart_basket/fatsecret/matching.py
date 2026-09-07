"""Explicit synthetic food/serving mapping. No lookup by invented provider IDs."""

from smart_basket.schemas import FatSecretItem, FatSecretPreviewMeal, UnresolvedFood

DEMO_FOODS = {"oats": "Dry oats", "rice": "Dry rice", "lentils": "Dry lentils"}


def match_personal_portion(meal, *, force_unmatched=False):
    items, unresolved = [], []
    for amount in meal.ingredient_amounts:
        if (force_unmatched or meal.source != "synthetic" or amount.ingredient_id not in DEMO_FOODS
                or amount.unit != "g" or amount.name != DEMO_FOODS.get(amount.ingredient_id)):
            unresolved.append(UnresolvedFood(ingredient_id=amount.ingredient_id,
                reason="No verified compatible food/serving mapping in the demo catalog."))
            continue
        personal_quantity = amount.quantity / meal.servings
        items.append(FatSecretItem(ingredient_id=amount.ingredient_id,
            food_id=f"demo-food-{amount.ingredient_id}", serving_id="demo-serving-100g-dry",
            matched_name=amount.name, number_of_units=personal_quantity / 100,
            source_quantity=personal_quantity, source_unit=amount.unit))
    if not meal.ingredient_amounts:
        unresolved.append(UnresolvedFood(ingredient_id="unknown", reason="Meal has no ingredient quantities."))
    return FatSecretPreviewMeal(meal_id=meal.id, title=meal.title,
        source_kcal_per_serving=meal.kcal_per_serving, fatsecret_kcal_per_serving=None,
        items=items, unresolved=unresolved)
