"""Original synthetic meals for local development and demo fallback."""

from __future__ import annotations

from .normalization import IngredientSpec, MealTemplate, aggregate_ingredients, build_meal_from_template

INGREDIENTS: dict[str, IngredientSpec] = {
    "oats": IngredientSpec(
        id="oats",
        name="Dry oats",
        search_terms=("oats",),
        quantity_per_serving=50.0,
        unit="g",
    ),
    "rice": IngredientSpec(
        id="rice",
        name="Dry rice",
        search_terms=("rice",),
        quantity_per_serving=80.0,
        unit="g",
    ),
    "lentils": IngredientSpec(
        id="lentils",
        name="Dry lentils",
        search_terms=("lentils",),
        quantity_per_serving=70.0,
        unit="g",
    ),
}


DAY_TEMPLATES: tuple[tuple[MealTemplate, MealTemplate, MealTemplate], ...] = (
    (
        MealTemplate(
            slot="breakfast",
            title="Oatmeal breakfast bowl",
            kcal_per_serving=420.0,
            ingredients=(INGREDIENTS["oats"],),
        ),
        MealTemplate(
            slot="lunch",
            title="Rice and lentil lunch bowl",
            kcal_per_serving=680.0,
            ingredients=(
                INGREDIENTS["rice"],
                IngredientSpec(
                    id="lentils",
                    name="Dry lentils",
                    search_terms=("lentils",),
                    quantity_per_serving=30.0,
                    unit="g",
                ),
            ),
        ),
        MealTemplate(
            slot="dinner",
            title="Lentil dinner stew",
            kcal_per_serving=760.0,
            ingredients=(
                INGREDIENTS["lentils"],
                IngredientSpec(
                    id="rice",
                    name="Dry rice",
                    search_terms=("rice",),
                    quantity_per_serving=40.0,
                    unit="g",
                ),
            ),
        ),
    ),
)


def build_synthetic_meal_plan(request, filters):
    meals = []
    for day in range(1, request.days + 1):
        templates = DAY_TEMPLATES[(day - 1) % len(DAY_TEMPLATES)]
        for index, template in enumerate(templates, start=1):
            meals.append(
                build_meal_from_template(
                    day=day,
                    index=index,
                    servings=request.people,
                    template=template,
                    restrictions=filters.restrictions,
                    source="synthetic",
                )
            )

    ingredients = aggregate_ingredients(meals, INGREDIENTS, filters.restrictions)
    warnings = [
        "Meal plan uses Sofiia synthetic fallback; live Edamam credentials are not configured.",
        "Synthetic recipes are original demo data and are not provider recipe payloads.",
    ]
    if request.calories_per_person_per_day is not None:
        warnings.append(
            "Calorie target is retained as a constraint, but synthetic fallback does not optimize calories."
        )

    return {
        "meals": meals,
        "ingredients": ingredients,
        "warnings": warnings,
        "source": "synthetic",
    }
