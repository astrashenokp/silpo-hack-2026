from collections import defaultdict

from smart_basket.catalog.matching import (
    line_total,
    purchase_quantity,
)
from smart_basket.schemas import (
    IngredientAmount,
    IngredientRequirement,
    Meal,
    ProductSelection,
)


# ============================================================
# MOCK SOFIIA
# Later replace with Sofiia's real build_meal_plan(...)
# ============================================================

def build_meal_plan(request, effective_context):
    """
    Temporary meal-plan generator.

    Creates:
    - breakfast -> oats
    - lunch -> rice
    - dinner -> lentils

    We intentionally use these three ingredients because
    Rina's DemoCatalog already contains matching products.
    """

    meals = []

    quantities = defaultdict(float)
    meal_ids = defaultdict(list)

    ingredient_names = {
        "oats": "Dry oats",
        "rice": "Dry rice",
        "lentils": "Dry lentils",
    }

    meal_templates = [
        {
            "slot": "breakfast",
            "ingredient_id": "oats",
            "title": "Oatmeal bowl",
            "quantity_per_person": 50.0,
            "kcal": 400.0,
        },
        {
            "slot": "lunch",
            "ingredient_id": "rice",
            "title": "Rice vegetable bowl",
            "quantity_per_person": 80.0,
            "kcal": 550.0,
        },
        {
            "slot": "dinner",
            "ingredient_id": "lentils",
            "title": "Lentil bowl",
            "quantity_per_person": 70.0,
            "kcal": 500.0,
        },
    ]

    for day in range(1, request.days + 1):

        for template in meal_templates:

            ingredient_id = template["ingredient_id"]

            meal_id = (
                f"mock-day-{day}-"
                f"{template['slot']}"
            )

            quantity = (
                template["quantity_per_person"]
                * request.people
            )

            quantities[ingredient_id] += quantity

            meal_ids[ingredient_id].append(
                meal_id
            )

            meals.append(
                Meal(
                    id=meal_id,
                    day=day,
                    slot=template["slot"],
                    title=template["title"],
                    servings=request.people,
                    kcal_per_serving=template["kcal"],
                    ingredient_ids=[
                        ingredient_id
                    ],
                    ingredient_amounts=[
                        IngredientAmount(
                            ingredient_id=ingredient_id,
                            name=ingredient_names[
                                ingredient_id
                            ],
                            quantity=quantity,
                            unit="g",
                        )
                    ],
                    source="synthetic",
                    source_url=None,
                    attribution=None,
                )
            )

    ingredients = []

    for ingredient_id, quantity in quantities.items():

        ingredients.append(
            IngredientRequirement(
                id=ingredient_id,
                name=ingredient_names[
                    ingredient_id
                ],
                search_terms=[
                    ingredient_id
                ],
                quantity=quantity,
                unit="g",
                meal_ids=meal_ids[
                    ingredient_id
                ],
                restrictions=request.restrictions,
            )
        )

    return {
        "meals": meals,
        "ingredients": ingredients,
        "warnings": [
            (
                "Meal plan uses mock data. "
                "Sofiia/Edamam is not connected yet."
            )
        ],
    }

