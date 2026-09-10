"""Original synthetic meals for local development and demo fallback."""

from __future__ import annotations

from .normalization import IngredientSpec, MealTemplate, aggregate_ingredients, build_meal_from_template
from .nutrition import ACCURACY_WARNINGS, calorie_target_for_slot, calorie_target_warnings, build_nutrition_summary

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
    (
        MealTemplate(
            slot="breakfast",
            title="Warm oat porridge with fruit",
            kcal_per_serving=430.0,
            ingredients=(INGREDIENTS["oats"],),
        ),
        MealTemplate(
            slot="lunch",
            title="Rice pilaf with lentils",
            kcal_per_serving=670.0,
            ingredients=(
                IngredientSpec(
                    id="rice",
                    name="Dry rice",
                    search_terms=("rice",),
                    quantity_per_serving=70.0,
                    unit="g",
                ),
                IngredientSpec(
                    id="lentils",
                    name="Dry lentils",
                    search_terms=("lentils",),
                    quantity_per_serving=40.0,
                    unit="g",
                ),
            ),
        ),
        MealTemplate(
            slot="dinner",
            title="Lentil and rice soup",
            kcal_per_serving=730.0,
            ingredients=(
                IngredientSpec(
                    id="lentils",
                    name="Dry lentils",
                    search_terms=("lentils",),
                    quantity_per_serving=60.0,
                    unit="g",
                ),
                IngredientSpec(
                    id="rice",
                    name="Dry rice",
                    search_terms=("rice",),
                    quantity_per_serving=50.0,
                    unit="g",
                ),
            ),
        ),
    ),
    (
        MealTemplate(
            slot="breakfast",
            title="Oat breakfast cup",
            kcal_per_serving=410.0,
            ingredients=(INGREDIENTS["oats"],),
        ),
        MealTemplate(
            slot="lunch",
            title="Rice bowl with lentil topping",
            kcal_per_serving=690.0,
            ingredients=(
                IngredientSpec(
                    id="rice",
                    name="Dry rice",
                    search_terms=("rice",),
                    quantity_per_serving=90.0,
                    unit="g",
                ),
                IngredientSpec(
                    id="lentils",
                    name="Dry lentils",
                    search_terms=("lentils",),
                    quantity_per_serving=20.0,
                    unit="g",
                ),
            ),
        ),
        MealTemplate(
            slot="dinner",
            title="Hearty lentil skillet",
            kcal_per_serving=780.0,
            ingredients=(
                IngredientSpec(
                    id="lentils",
                    name="Dry lentils",
                    search_terms=("lentils",),
                    quantity_per_serving=80.0,
                    unit="g",
                ),
                IngredientSpec(
                    id="rice",
                    name="Dry rice",
                    search_terms=("rice",),
                    quantity_per_serving=30.0,
                    unit="g",
                ),
            ),
        ),
    ),
    (
        MealTemplate(
            slot="breakfast",
            title="Simple overnight oats",
            kcal_per_serving=420.0,
            ingredients=(INGREDIENTS["oats"],),
        ),
        MealTemplate(
            slot="lunch",
            title="Balanced rice and lentils",
            kcal_per_serving=700.0,
            ingredients=(
                IngredientSpec(
                    id="rice",
                    name="Dry rice",
                    search_terms=("rice",),
                    quantity_per_serving=60.0,
                    unit="g",
                ),
                IngredientSpec(
                    id="lentils",
                    name="Dry lentils",
                    search_terms=("lentils",),
                    quantity_per_serving=50.0,
                    unit="g",
                ),
            ),
        ),
        MealTemplate(
            slot="dinner",
            title="Lentil rice supper bowl",
            kcal_per_serving=740.0,
            ingredients=(
                IngredientSpec(
                    id="lentils",
                    name="Dry lentils",
                    search_terms=("lentils",),
                    quantity_per_serving=50.0,
                    unit="g",
                ),
                IngredientSpec(
                    id="rice",
                    name="Dry rice",
                    search_terms=("rice",),
                    quantity_per_serving=60.0,
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
                    calorie_target=calorie_target_for_slot(
                        request.calories_per_person_per_day,
                        template.slot,
                    ),
                )
            )

    ingredients = aggregate_ingredients(meals, INGREDIENTS, filters.restrictions)
    nutrition_summary = build_nutrition_summary(request, meals)
    warnings = [
        "Meal plan uses Sofiia synthetic fallback; live Edamam credentials are not configured.",
        "Synthetic recipes are original demo data and are not provider recipe payloads.",
        *ACCURACY_WARNINGS,
        *calorie_target_warnings(nutrition_summary),
    ]
    if request.calories_per_person_per_day is not None:
        warnings.append(
            "Calorie target metadata uses a 25/35/40 breakfast/lunch/dinner split; synthetic fallback does not run ILP optimization."
        )

    return {
        "meals": meals,
        "nutrition_summary": nutrition_summary,
        "ingredients": ingredients,
        "warnings": warnings,
        "source": "synthetic",
    }
